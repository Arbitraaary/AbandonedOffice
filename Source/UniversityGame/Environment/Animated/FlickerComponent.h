// Faulty wiring: drives the brightness of some lights and emissive materials of its owner.
// Long calm periods (a slight buzz), then a burst of fast random flickering, now and then the light dies
// for a moment before it comes back. Every component has its own random rhythm.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FlickerComponent.generated.h"

class ULightComponent;
class UMaterialInstanceDynamic;

UCLASS(ClassGroup = (Lab6), meta = (BlueprintSpawnableComponent))
class UNIVERSITYGAME_API UFlickerComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UFlickerComponent();

	// seconds between bursts
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	float MinCalm = 1.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	float MaxCalm = 6.f;

	// length of a burst of flickering, seconds
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	float MinBurst = 0.25f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	float MaxBurst = 1.2f;

	// switches per second during a burst
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	float FlickerRate = 16.f;

	// brightness when "off" (0..1 of the normal brightness)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	float OffLevel = 0.03f;

	// chance that a burst ends with the light dead for a moment
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	float DeadChance = 0.3f;

	// a movable light (its current intensity is the "on" brightness)
	void AddLight(ULightComponent* Light);

	// an emissive material parameter (its current value is the "on" value)
	void AddMaterial(UMaterialInstanceDynamic* Material, FName Parameter);

	float GetLevel() const { return Level; }

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void BeginPlay() override;

private:
	enum class EState : uint8 { Calm, Burst, Dead };

	struct FLit
	{
		TWeakObjectPtr<ULightComponent> Light;
		float Base = 0.f;
	};

	struct FGlow
	{
		TWeakObjectPtr<UMaterialInstanceDynamic> Material;
		FName Parameter;
		float Base = 0.f;
	};

	void Apply();

	TArray<FLit> Lights;
	TArray<FGlow> Glows;
	EState State = EState::Calm;
	float Level = 1.f;
	float StateEnd = 0.f;
	float NextSwitch = 0.f;
};
