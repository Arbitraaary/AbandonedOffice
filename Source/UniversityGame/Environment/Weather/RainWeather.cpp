#include "RainWeather.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"
#include "UObject/ConstructorHelpers.h"

namespace RainLook
{
	const FVector DropScale(0.012f, 0.012f, 0.55f);     // engine cube 100 cm -> a 1.2 x 1.2 x 55 cm streak
	constexpr float SpawnAbove = 1300.f;                // drops appear this far above the camera
}

ARainWeather::ARainWeather()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	Drops = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Drops"));
	Drops->SetupAttachment(RootComponent);
	Drops->SetStaticMesh(Cube.Object);
	Drops->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Drops->SetCastShadow(false);
	Drops->SetAbsolute(true, true, true);
	Drops->SetMobility(EComponentMobility::Movable);
	Drops->SetCanEverAffectNavigation(false);

	Lightning = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Lightning"));
	Lightning->SetupAttachment(RootComponent);
	Lightning->SetMobility(EComponentMobility::Movable);
	Lightning->SetRelativeRotation(FRotator(-55.f, 40.f, 0.f));
	Lightning->SetLightColor(FLinearColor(0.75f, 0.82f, 1.f));
	Lightning->SetIntensity(0.f);
	Lightning->SetAtmosphereSunLight(false);
	Lightning->ForwardShadingPriority = 0;
	Lightning->SetCastShadows(true);
}

void ARainWeather::BeginPlay()
{
	Super::BeginPlay();
	if (DropMaterial)
	{
		Drops->SetMaterial(0, DropMaterial);
	}
	Pool.SetNum(MaxDrops);
	TArray<FTransform> Hidden;
	Hidden.Init(FTransform(FQuat::Identity, FVector::ZeroVector, FVector::ZeroVector), MaxDrops);
	Drops->AddInstances(Hidden, false);

	const float Now = GetWorld()->GetTimeSeconds();
	Phase = bStartRaining ? EPhase::Starting : EPhase::Clear;
	PhaseEnd = Now + (bStartRaining ? RampTime : FMath::FRandRange(ClearTime.X, ClearTime.Y));
}

void ARainWeather::Tick(const float DeltaTime)
{
	Super::Tick(DeltaTime);
	UpdateWeather(DeltaTime);
	UpdateDrops(DeltaTime);
	UpdateLightning(DeltaTime);
}

void ARainWeather::UpdateWeather(const float DeltaTime)
{
	const float Now = GetWorld()->GetTimeSeconds();
	switch (Phase)
	{
	case EPhase::Clear:
		Strength = 0.f;
		if (Now >= PhaseEnd) { Phase = EPhase::Starting; PhaseEnd = Now + RampTime; }
		break;
	case EPhase::Starting:
		Strength = FMath::Min(Strength + DeltaTime / FMath::Max(RampTime, 0.1f), 1.f);
		if (Now >= PhaseEnd)
		{
			Phase = EPhase::Raining;
			PhaseEnd = Now + FMath::FRandRange(RainTime.X, RainTime.Y);
			NextFlash = Now + FMath::FRandRange(3.f, 10.f);
		}
		break;
	case EPhase::Raining:
		Strength = FMath::Clamp(Strength + FMath::FRandRange(-0.15f, 0.15f) * DeltaTime, 0.75f, 1.f);   // gusts
		if (Now >= PhaseEnd) { Phase = EPhase::Stopping; PhaseEnd = Now + RampTime; }
		break;
	case EPhase::Stopping:
		Strength = FMath::Max(Strength - DeltaTime / FMath::Max(RampTime, 0.1f), 0.f);
		if (Now >= PhaseEnd)
		{
			Phase = EPhase::Clear;
			Strength = 0.f;
			PhaseEnd = Now + FMath::FRandRange(ClearTime.X, ClearTime.Y);
		}
		break;
	}
}

FVector ARainWeather::ViewCentre() const
{
	if (const APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		return Cam->GetCameraLocation();
	}
	return GetActorLocation();
}

void ARainWeather::Respawn(FDrop& Drop, const FVector& Centre, const bool bAnyHeight)
{
	const float R = Radius * FMath::Sqrt(FMath::FRand());
	const float A = FMath::FRandRange(0.f, 2.f * PI);
	const float Z = Centre.Z + (bAnyHeight ? FMath::FRandRange(-300.f, RainLook::SpawnAbove) : RainLook::SpawnAbove);
	Drop.Pos = FVector(Centre.X + R * FMath::Cos(A), Centre.Y + R * FMath::Sin(A), Z);

	// the first surface under the drop: roof, ground, a car... - it ends there (no rain inside the building)
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(RainDrop), false);
	const FVector Fall = FVector(Wind.X, Wind.Y, -FallSpeed).GetSafeNormal();
	const FVector End = Drop.Pos + Fall * 6000.f;
	Drop.EndZ = GetWorld()->LineTraceSingleByChannel(Hit, Drop.Pos, End, ECC_Visibility, Params) ? Hit.ImpactPoint.Z : End.Z;
	Drop.bActive = Drop.Pos.Z > Drop.EndZ;
}

void ARainWeather::UpdateDrops(const float DeltaTime)
{
	const int32 Wanted = FMath::RoundToInt(MaxDrops * Strength);
	if (Wanted == 0 && ActiveDrops == 0) return;               // dry: nothing to move

	const FVector Centre = ViewCentre();
	const FVector Velocity(Wind.X, Wind.Y, -FallSpeed);
	const FQuat Tilt = FRotationMatrix::MakeFromZ(-Velocity).ToQuat();       // streaks lean with the wind
	const FTransform HiddenT(FQuat::Identity, FVector::ZeroVector, FVector::ZeroVector);

	Transforms.SetNum(Pool.Num(), EAllowShrinking::No);
	ActiveDrops = 0;
	for (int32 i = 0; i < Pool.Num(); ++i)
	{
		FDrop& D = Pool[i];
		const bool bWanted = i < Wanted;
		if (D.bActive)
		{
			D.Pos += Velocity * DeltaTime;
			const bool bLanded = D.Pos.Z <= D.EndZ;
			const bool bAway = FVector::DistSquared2D(D.Pos, Centre) > FMath::Square(Radius * 1.3f);
			if (bLanded || bAway)
			{
				D.bActive = false;
				if (bWanted) Respawn(D, Centre, bAway);
			}
		}
		else if (bWanted)
		{
			Respawn(D, Centre, true);
		}
		ActiveDrops += D.bActive ? 1 : 0;
		Transforms[i] = D.bActive ? FTransform(Tilt, D.Pos, RainLook::DropScale) : HiddenT;
	}
	Drops->BatchUpdateInstancesTransforms(0, Transforms, true, true, true);
}

void ARainWeather::UpdateLightning(const float DeltaTime)
{
	const float Now = GetWorld()->GetTimeSeconds();
	if (Phase == EPhase::Raining && FlashTime < 0.f && Now >= NextFlash)
	{
		FlashTime = 0.f;
		FlashStrikes = FMath::RandRange(1, 3);
		Lightning->SetRelativeRotation(FRotator(FMath::FRandRange(-70.f, -35.f), FMath::FRandRange(0.f, 360.f), 0.f));
	}
	if (FlashTime >= 0.f)
	{
		FlashTime += DeltaTime;
		// a few short strikes, each a bright flash that fades fast
		const float StrikeLen = 0.18f;
		const float Local = FMath::Fmod(FlashTime, StrikeLen);
		const float K = FMath::Exp(-Local * 22.f);
		Lightning->SetIntensity(12.f * K * Strength);
		if (FlashTime >= StrikeLen * FlashStrikes)
		{
			FlashTime = -1.f;
			Lightning->SetIntensity(0.f);
			NextFlash = Now + FMath::FRandRange(6.f, 18.f);
		}
	}
}
