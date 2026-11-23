#include "FlickerComponent.h"

#include "Components/LightComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

UFlickerComponent::UFlickerComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

void UFlickerComponent::BeginPlay()
{
	Super::BeginPlay();
	State = EState::Calm;
	StateEnd = GetWorld()->GetTimeSeconds() + FMath::FRandRange(0.f, MaxCalm);   // lamps do not start in sync
}

void UFlickerComponent::AddLight(ULightComponent* Light)
{
	if (!Light) return;
	if (Light->Mobility != EComponentMobility::Movable)
	{
		UE_LOG(LogTemp, Warning, TEXT("Flicker: %s is not movable, its brightness cannot change in game"), *Light->GetReadableName());
		return;
	}
	Lights.Add({Light, Light->Intensity});
}

void UFlickerComponent::AddMaterial(UMaterialInstanceDynamic* Material, const FName Parameter)
{
	if (!Material) return;
	float Value = 1.f;
	Material->GetScalarParameterValue(FHashedMaterialParameterInfo(Parameter), Value);
	Glows.Add({Material, Parameter, Value});
}

void UFlickerComponent::TickComponent(const float DeltaTime, const ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	const float Now = GetWorld()->GetTimeSeconds();

	switch (State)
	{
	case EState::Calm:
		Level = FMath::FRandRange(0.95f, 1.f);                              // the usual fluorescent buzz
		if (Now >= StateEnd)
		{
			State = EState::Burst;
			StateEnd = Now + FMath::FRandRange(MinBurst, MaxBurst);
			NextSwitch = Now;
		}
		break;
	case EState::Burst:
		if (Now >= NextSwitch)
		{
			Level = FMath::RandBool() ? FMath::FRandRange(OffLevel, 0.35f) : FMath::FRandRange(0.7f, 1.f);
			NextSwitch = Now + FMath::FRandRange(0.5f, 1.5f) / FMath::Max(FlickerRate, 1.f);
		}
		if (Now >= StateEnd)
		{
			const bool bDie = FMath::FRand() < DeadChance;
			State = bDie ? EState::Dead : EState::Calm;
			StateEnd = Now + (bDie ? FMath::FRandRange(0.3f, 1.5f) : FMath::FRandRange(MinCalm, MaxCalm));
		}
		break;
	case EState::Dead:
		Level = OffLevel;
		if (Now >= StateEnd)
		{
			State = EState::Burst;                                           // it struggles back on
			StateEnd = Now + FMath::FRandRange(MinBurst, MaxBurst) * 0.6f;
			NextSwitch = Now;
		}
		break;
	}
	Apply();
}

void UFlickerComponent::Apply()
{
	for (const FLit& L : Lights)
	{
		if (ULightComponent* Light = L.Light.Get())
		{
			Light->SetIntensity(L.Base * Level);
		}
	}
	for (const FGlow& G : Glows)
	{
		if (UMaterialInstanceDynamic* M = G.Material.Get())
		{
			M->SetScalarParameterValue(G.Parameter, G.Base * Level);
		}
	}
}
