#include "SlidingGlassDoor.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Curves/CurveFloat.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"
#include "UObject/ConstructorHelpers.h"

namespace DoorParts
{
	// glass pane + 4 metal profiles per leaf
	constexpr int32 Count = 5;
	constexpr float Frame = 5.f;          // profile width, cm
	constexpr float Thick = 4.f;          // leaf thickness, cm
}

ASlidingGlassDoor::ASlidingGlassDoor()
{
	PrimaryActorTick.bCanEverTick = true;
	Tags.Add(FName("NoBodyPush"));          // a dead guard may fall against it without being lifted onto it
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	LeftLeaf = CreateDefaultSubobject<USceneComponent>(TEXT("LeftLeaf"));
	LeftLeaf->SetupAttachment(RootComponent);
	RightLeaf = CreateDefaultSubobject<USceneComponent>(TEXT("RightLeaf"));
	RightLeaf->SetupAttachment(RootComponent);
	for (int32 i = 0; i < DoorParts::Count; ++i)
	{
		for (int32 Side = 0; Side < 2; ++Side)
		{
			UStaticMeshComponent* Part = CreateDefaultSubobject<UStaticMeshComponent>(
				*FString::Printf(TEXT("%s_%d"), Side ? TEXT("Right") : TEXT("Left"), i));
			Part->SetupAttachment(Side ? RightLeaf : LeftLeaf);
			Part->SetStaticMesh(Cube.Object);
			Part->SetCollisionProfileName(TEXT("BlockAll"));
			Part->SetCanEverAffectNavigation(false);
			(Side ? RightParts : LeftParts).Add(Part);
		}
	}

	Sensor = CreateDefaultSubobject<UBoxComponent>(TEXT("Sensor"));
	Sensor->SetupAttachment(RootComponent);
	Sensor->SetCollisionProfileName(TEXT("Trigger"));
	Sensor->SetBoxExtent(FVector(170.f, 260.f, 120.f));
	Sensor->SetRelativeLocation(FVector(0.f, 0.f, 120.f));

	DoorTimeline = CreateDefaultSubobject<UTimelineComponent>(TEXT("DoorTimeline"));
}

void ASlidingGlassDoor::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	BuildLeaf(LeftLeaf, LeftParts, -1.f);
	BuildLeaf(RightLeaf, RightParts, 1.f);
	PlaceLeaves();
}

void ASlidingGlassDoor::BuildLeaf(USceneComponent* Leaf, const TArray<UStaticMeshComponent*>& Parts, const float Sign)
{
	// a leaf is half the opening wide; its local origin is its inner (meeting) edge at the threshold
	using namespace DoorParts;
	const float W = DoorWidth * 0.5f + 2.f;     // a little overlap in the middle
	const float Hh = DoorHeight;
	// cube is 100 cm: scale = size / 100; location = centre
	struct FPart { FVector Centre; FVector Size; bool bGlass; };
	const FPart Spec[Count] = {
		{FVector(Sign * W * 0.5f, 0.f, Hh * 0.5f), FVector(W - 2 * Frame, 1.2f, Hh - 2 * Frame), true},   // glass
		{FVector(Sign * Frame * 0.5f, 0.f, Hh * 0.5f), FVector(Frame, Thick, Hh), false},                  // inner stile
		{FVector(Sign * (W - Frame * 0.5f), 0.f, Hh * 0.5f), FVector(Frame, Thick, Hh), false},            // outer stile
		{FVector(Sign * W * 0.5f, 0.f, Frame * 0.5f + 6.f), FVector(W, Thick, Frame * 2.f + 4.f), false},   // bottom rail
		{FVector(Sign * W * 0.5f, 0.f, Hh - Frame * 0.5f), FVector(W, Thick, Frame), false},               // top rail
	};
	for (int32 i = 0; i < Count && i < Parts.Num(); ++i)
	{
		UStaticMeshComponent* Part = Parts[i];
		Part->SetRelativeLocation(Spec[i].Centre);
		Part->SetRelativeScale3D(Spec[i].Size / 100.f);
		if (UMaterialInterface* M = Spec[i].bGlass ? GlassMaterial : FrameMaterial)
		{
			Part->SetMaterial(0, M);
		}
		Part->SetCastShadow(!Spec[i].bGlass);
	}
	Leaf->SetRelativeLocation(FVector::ZeroVector);
}

void ASlidingGlassDoor::BeginPlay()
{
	Super::BeginPlay();
	Tags.AddUnique(FName("NoBodyPush"));      // also on doors placed before (the setup script rewrites the tags)
	if (!OpenCurve)
	{
		// jerk open -> slip back -> jerk -> stick, over 2 seconds (values are scaled by StuckAt in OnOpenProgress)
		OpenCurve = NewObject<UCurveFloat>(this, TEXT("DoorOpenCurve"));
		const TArray<TPair<float, float>> Keys = {
			{0.0f, 0.0f}, {0.25f, 0.40f}, {0.38f, 0.22f}, {0.70f, 0.85f}, {0.85f, 0.72f}, {1.15f, 1.05f}, {1.30f, 0.97f}, {2.0f, 1.0f}};
		for (const TPair<float, float>& K : Keys)
		{
			const FKeyHandle H = OpenCurve->FloatCurve.AddKey(K.Key, K.Value);
			OpenCurve->FloatCurve.SetKeyInterpMode(H, RCIM_Linear);
		}
	}
	FOnTimelineFloat Progress;
	Progress.BindUFunction(this, FName("OnOpenProgress"));
	DoorTimeline->AddInterpFloat(OpenCurve, Progress);
	DoorTimeline->SetLooping(false);

	Sensor->OnComponentBeginOverlap.AddDynamic(this, &ASlidingGlassDoor::OnSensorBegin);
	Sensor->OnComponentEndOverlap.AddDynamic(this, &ASlidingGlassDoor::OnSensorEnd);
}

bool ASlidingGlassDoor::IsPlayer(const AActor* Actor) const
{
	// the sensor reacts to anybody walking up to it: the player and the guards (a dead body has no collision)
	const APawn* Pawn = Cast<APawn>(Actor);
	return Pawn && !Pawn->IsPendingKillPending();
}

int32 ASlidingGlassDoor::CountPeopleInside() const
{
	TArray<AActor*> Overlapping;
	Sensor->GetOverlappingActors(Overlapping, APawn::StaticClass());
	int32 N = 0;
	for (const AActor* A : Overlapping)
	{
		N += IsPlayer(A) ? 1 : 0;
	}
	return N;
}

void ASlidingGlassDoor::OnSensorBegin(UPrimitiveComponent*, AActor* OtherActor, UPrimitiveComponent*, int32, bool, const FHitResult&)
{
	if (!IsPlayer(OtherActor)) return;
	const bool bWasEmpty = PlayersInside == 0;
	PlayersInside = FMath::Max(CountPeopleInside(), 1);
	if (bWasEmpty)
	{
		DoorTimeline->SetPlayRate(1.f);
		DoorTimeline->Play();                         // from where it is now: it can re-open half closed
	}
}

void ASlidingGlassDoor::OnSensorEnd(UPrimitiveComponent*, AActor* OtherActor, UPrimitiveComponent*, int32)
{
	if (!IsPlayer(OtherActor)) return;
	PlayersInside = CountPeopleInside();
	if (PlayersInside == 0)
	{
		DoorTimeline->SetPlayRate(1.3f);              // closes the same jerky way, a bit faster
		DoorTimeline->Reverse();
	}
}

void ASlidingGlassDoor::OnOpenProgress(const float Value)
{
	OpenAmount = FMath::Clamp(Value, 0.f, 1.2f) * StuckAt;
	PlaceLeaves();
}

void ASlidingGlassDoor::Tick(const float DeltaTime)
{
	Super::Tick(DeltaTime);
	// stuck half open: now and then the motor tries again and the leaves shudder
	const float Now = GetWorld()->GetTimeSeconds();
	if (PlayersInside > 0 && !DoorTimeline->IsPlaying() && OpenAmount > 0.1f)
	{
		if (Now >= NextShudder)
		{
			NextShudder = Now + FMath::FRandRange(1.5f, 3.5f);
			Shudder = 0.6f;
		}
	}
	if (Shudder > 0.f)
	{
		Shudder = FMath::Max(Shudder - DeltaTime, 0.f);
		PlaceLeaves();
	}
}

void ASlidingGlassDoor::PlaceLeaves()
{
	const float Travel = DoorWidth * 0.5f;
	const float Shake = Shudder > 0.f ? FMath::Sin(Shudder * 70.f) * 2.5f * Shudder : 0.f;
	const float Offset = OpenAmount * Travel + Shake;
	LeftLeaf->SetRelativeLocation(FVector(-Offset, 0.f, 0.f));
	RightLeaf->SetRelativeLocation(FVector(Offset, 0.f, 0.f));
}
