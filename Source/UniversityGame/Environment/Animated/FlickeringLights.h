// Placed on the level: makes some of the existing ceiling lights flicker (bad wiring in the abandoned office).
// For every target actor: its movable lights change brightness, and the lamp meshes' emissive parameter
// ("Emission" on the office-pack lamp material) follows, so the fixture itself goes dark too.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FlickeringLights.generated.h"

UCLASS()
class UNIVERSITYGAME_API AFlickeringLights : public AActor
{
	GENERATED_BODY()

public:
	AFlickeringLights();

	// lamps and lights to flicker; each one gets its own random rhythm
	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Flicker")
	TArray<TObjectPtr<AActor>> Targets;

	// seconds of steady light between flicker bursts
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	float MinCalm = 0.8f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	float MaxCalm = 3.5f;

	// emissive scalar parameter of the lamp materials
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
	FName EmissiveParameter = TEXT("Emission");

protected:
	virtual void BeginPlay() override;
};
