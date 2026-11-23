// A fluorescent office lamp that tore off one of its two cables: it hangs from the ceiling on the other one and swings.
// Modelled and animated in Blender (SK_HangingLamp + A_HangingLamp_Swing, bones root - cable_01..03 - lamp - dangle_01..02, light).
// The light is attached to the "light" bone, so it swings together with the lamp; the tubes and the light flicker.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HangingLamp.generated.h"

class USkeletalMeshComponent;
class URectLightComponent;
class UPointLightComponent;
class UAnimSequence;
class UFlickerComponent;

UCLASS()
class UNIVERSITYGAME_API AHangingLamp : public AActor
{
	GENERATED_BODY()

public:
	AHangingLamp();

	// the actor's origin is the anchor in the ceiling
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Lamp")
	USkeletalMeshComponent* Mesh;

	// light from the open side of the fixture (attached to the "light" bone)
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Lamp")
	URectLightComponent* TubeLight;

	// soft light all round the lamp
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Lamp")
	UPointLightComponent* Glow;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Lamp")
	UFlickerComponent* Flicker;

	// looping swing made in Blender
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lamp")
	UAnimSequence* SwingAnimation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lamp")
	float SwingPlayRate = 1.f;

	// material slot of the tubes and its emissive scalar parameter
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lamp")
	int32 TubeMaterialIndex = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Lamp")
	FName TubeGlowParameter = TEXT("Glow");

protected:
	virtual void BeginPlay() override;
};
