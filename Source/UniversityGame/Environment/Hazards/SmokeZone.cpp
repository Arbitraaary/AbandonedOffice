#include "SmokeZone.h"

#include "Components/BoxComponent.h"
#include "Components/LocalFogVolumeComponent.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "UObject/ConstructorHelpers.h"

ASmokeZone::ASmokeZone()
{
	PrimaryActorTick.bCanEverTick = false;

	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));   // = centre of the smoky floor
	Zone = CreateDefaultSubobject<UBoxComponent>(TEXT("Zone"));
	Zone->SetupAttachment(RootComponent);
	Zone->SetCollisionProfileName(TEXT("Trigger"));
	Zone->SetGenerateOverlapEvents(true);
	Zone->SetBoxExtent(ZoneExtent);
	Zone->SetRelativeLocation(FVector(0.f, 0.f, ZoneExtent.Z));
	Zone->ShapeColor = FColor(160, 160, 160);

	// the dense part of the smoke: a volumetric fog ellipsoid over the zone (unit sphere = 500 cm radius)
	Haze = CreateDefaultSubobject<ULocalFogVolumeComponent>(TEXT("Haze"));
	Haze->SetupAttachment(RootComponent);

	static ConstructorHelpers::FObjectFinder<UParticleSystem> Steam(TEXT("/Game/OrionMars/Particles/P_Steam.P_Steam"));
	if (Steam.Succeeded())
	{
		SmokeParticles = Steam.Object;
	}
}

void ASmokeZone::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	// the box sits on the floor: the actor's location is the floor centre
	Zone->SetBoxExtent(ZoneExtent);
	Zone->SetRelativeLocation(FVector(0.f, 0.f, ZoneExtent.Z));

	Haze->SetRelativeLocation(FVector(0.f, 0.f, ZoneExtent.Z * 0.8f));
	Haze->SetRelativeScale3D(FVector(ZoneExtent.X * 1.25f, ZoneExtent.Y * 1.25f, ZoneExtent.Z * 1.4f) / 500.f);
	Haze->SetRadialFogExtinction(HazeDensity);
	Haze->SetHeightFogExtinction(HazeDensity * 0.5f);
	Haze->SetHeightFogFalloff(800.f);
	Haze->SetFogAlbedo(HazeColor);
	Haze->SetFogPhaseG(0.1f);

	for (UParticleSystemComponent* P : Puffs)
	{
		if (P) P->DestroyComponent();
	}
	Puffs.Reset();
	if (!SmokeParticles) return;

	// a grid of smoke sources over the floor of the zone (a little random so it does not look like a grid)
	const int32 NX = FMath::Max(1, FMath::RoundToInt(ZoneExtent.X * 2.f / PuffSpacing));
	const int32 NY = FMath::Max(1, FMath::RoundToInt(ZoneExtent.Y * 2.f / PuffSpacing));
	FRandomStream Rng(GetUniqueID());
	for (int32 Layer = 0; Layer < FMath::Max(1, SmokeLayers); ++Layer)
	{
		for (int32 ix = 0; ix < NX; ++ix)
		{
			for (int32 iy = 0; iy < NY; ++iy)
			{
				const FVector Local((ix + 0.5f) / NX * 2.f - 1.f, (iy + 0.5f) / NY * 2.f - 1.f, 0.f);
				FVector Offset(Local.X * ZoneExtent.X * 0.85f, Local.Y * ZoneExtent.Y * 0.85f,
				               Layer * ZoneExtent.Z * 0.7f + Rng.FRandRange(0.f, 30.f));
				Offset.X += Rng.FRandRange(-0.3f, 0.3f) * PuffSpacing;
				Offset.Y += Rng.FRandRange(-0.3f, 0.3f) * PuffSpacing;
				UParticleSystemComponent* P = NewObject<UParticleSystemComponent>(this);
				P->SetTemplate(SmokeParticles);
				P->SetupAttachment(RootComponent);
				P->SetWorldLocation(GetActorLocation() + GetActorRotation().RotateVector(Offset));
				P->SetWorldScale3D(FVector(PuffScale * Rng.FRandRange(0.85f, 1.2f)));
				P->CustomTimeDilation = SmokeSpeed * Rng.FRandRange(0.85f, 1.15f);   // slow, heavy smoke
				P->bAutoActivate = true;
				P->CreationMethod = EComponentCreationMethod::UserConstructionScript;   // rebuilt with the actor
				P->RegisterComponent();
				Puffs.Add(P);
			}
		}
	}
}

bool ASmokeZone::IsActorInSmoke(const AActor* Actor)
{
	if (!Actor) return false;
	TArray<AActor*> Zones;
	Actor->GetOverlappingActors(Zones, ASmokeZone::StaticClass());
	return Zones.Num() > 0;
}
