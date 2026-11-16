#include "SparkingCables.h"

#include "Components/BoxComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "UniversityGame/Enemies/SecurityGuard/SecurityGuard.h"

ASparkingCables::ASparkingCables()
{
	PrimaryActorTick.bCanEverTick = true;

	Cables = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Cables"));
	Cables->SetCollisionEnabled(ECollisionEnabled::NoCollision);       // the player walks through them
	RootComponent = Cables;

	// the shock area: around the cables lying on the floor and hanging above it
	ShockZone = CreateDefaultSubobject<UBoxComponent>(TEXT("ShockZone"));
	ShockZone->SetupAttachment(Cables);
	ShockZone->SetCollisionProfileName(TEXT("Trigger"));
	ShockZone->SetGenerateOverlapEvents(true);
	ShockZone->SetBoxExtent(FVector(110.f, 110.f, 90.f));
	ShockZone->ShapeColor = FColor(255, 200, 40);

	Sparks = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Sparks"));
	Sparks->SetupAttachment(Cables);
	Sparks->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Sparks->SetCastShadow(false);
	Sparks->SetAbsolute(true, true, true);             // instances are given in world space
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded()) Sparks->SetStaticMesh(Cube.Object);

	Flash = CreateDefaultSubobject<UPointLightComponent>(TEXT("Flash"));
	Flash->SetupAttachment(Cables);
	Flash->SetIntensity(0.f);
	Flash->SetLightColor(FLinearColor(0.75f, 0.85f, 1.f));          // electric blue-white
	Flash->SetAttenuationRadius(450.f);
	Flash->SetCastShadows(false);
}

void ASparkingCables::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	ShockZone->SetRelativeLocation(FVector(0.f, 0.f, -CeilingHeight + 90.f));
	Flash->SetRelativeLocation(FVector(0.f, 0.f, -CeilingHeight + 40.f));
	if (SparkMaterial) Sparks->SetMaterial(0, SparkMaterial);
}

void ASparkingCables::BeginPlay()
{
	Super::BeginPlay();
	FloorZ = GetActorLocation().Z - CeilingHeight;
	SparkPoints.Reset();
	for (const FName& S : Cables->GetAllSocketNames())
	{
		if (S.ToString().StartsWith(TEXT("Spark"))) SparkPoints.Add(Cables->GetSocketLocation(S));
	}
	if (SparkPoints.Num() == 0)                         // no sockets: somewhere on the floor under the actor
	{
		SparkPoints.Add(GetActorLocation() - FVector(0.f, 0.f, CeilingHeight - 5.f));
	}
	NextBurst = GetWorld()->GetTimeSeconds() + 0.5f;
}

FVector ASparkingCables::RandomSparkPoint() const
{
	return SparkPoints[FMath::RandRange(0, SparkPoints.Num() - 1)];
}

void ASparkingCables::Burst(const FVector& Where, const int32 Count, const float Speed)
{
	for (int32 i = 0; i < Count; ++i)
	{
		FSpark S;
		S.Pos = Where;
		S.Vel = FMath::VRandCone(FVector::UpVector, FMath::DegreesToRadians(75.f)) * Speed * FMath::FRandRange(0.4f, 1.f);
		S.MaxLife = S.Life = FMath::FRandRange(0.25f, 0.75f);
		Live.Add(S);
	}
	FlashLevel = 1.f;
	Flash->SetWorldLocation(Where + FVector(0.f, 0.f, 15.f));
}

void ASparkingCables::Tick(const float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const float Now = GetWorld()->GetTimeSeconds();

	// random bursts from the copper ends: sometimes a single crackle, sometimes a big shower
	if (Now >= NextBurst)
	{
		const bool bBig = FMath::FRand() < 0.3f;
		Burst(RandomSparkPoint(), bBig ? FMath::RandRange(18, 28) : FMath::RandRange(5, 10), bBig ? 420.f : 260.f);
		NextBurst = Now + FMath::FRandRange(BurstInterval.X, BurstInterval.Y);
	}

	// simulate the sparks: gravity, bounce on the floor, die out
	Sparks->ClearInstances();
	for (int32 i = Live.Num() - 1; i >= 0; --i)
	{
		FSpark& S = Live[i];
		S.Life -= DeltaSeconds;
		if (S.Life <= 0.f)
		{
			Live.RemoveAtSwap(i);
			continue;
		}
		S.Vel.Z -= 980.f * DeltaSeconds;
		S.Pos += S.Vel * DeltaSeconds;
		if (S.Pos.Z < FloorZ + 1.f)
		{
			S.Pos.Z = FloorZ + 1.f;
			S.Vel.Z = -S.Vel.Z * 0.3f;
			S.Vel.X *= 0.6f;
			S.Vel.Y *= 0.6f;
		}
		// a streak along the velocity, shrinking as it dies (engine cube = 100 cm)
		const float Fade = S.Life / S.MaxLife;
		const float Len = FMath::Clamp(S.Vel.Size() * 0.00018f, 0.012f, 0.08f) * (0.5f + 0.5f * Fade);
		const float Thick = 0.004f * (0.4f + 0.6f * Fade);
		const FRotator Rot = S.Vel.IsNearlyZero() ? FRotator::ZeroRotator : S.Vel.Rotation();
		Sparks->AddInstance(FTransform(Rot, S.Pos, FVector(Len, Thick, Thick)), true);
	}

	// the light flickers with the sparks
	FlashLevel = FMath::Max(0.f, FlashLevel - DeltaSeconds * 6.f);
	Flash->SetIntensity(FlashLevel * FMath::FRandRange(3000.f, 9000.f));

	ShockOverlappingGuards();
}

void ASparkingCables::NotifyActorBeginOverlap(AActor* OtherActor)
{
	Super::NotifyActorBeginOverlap(OtherActor);
	ShockOverlappingGuards();
}

void ASparkingCables::ShockOverlappingGuards()
{
	const float Now = GetWorld()->GetTimeSeconds();
	TArray<AActor*> Inside;
	ShockZone->GetOverlappingActors(Inside, ASecurityGuard::StaticClass());
	for (AActor* A : Inside)
	{
		ASecurityGuard* Guard = Cast<ASecurityGuard>(A);
		if (!Guard || Guard->IsDead()) continue;
		const float* Last = LastShock.Find(Guard);
		if (Last && Now - *Last < ShockCooldown) continue;
		LastShock.Add(Guard, Now);
		Burst(Guard->GetActorLocation() - FVector(0.f, 0.f, 40.f), 30, 450.f);   // big shower where he touched them
		Guard->Electrocute(ShockDamage, StunTime, this);
	}
}
