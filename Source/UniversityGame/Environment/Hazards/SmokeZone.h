// Obstacle for the security guard: a cloud of thick smoke from a smouldering cable fire ("blind zone").
//  * the player inside the smoke is invisible to guards - they lose him and come to search where he disappeared;
//  * a guard inside the smoke sees nothing at all and can only walk slowly, coughing his way out.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SmokeZone.generated.h"

class UBoxComponent;
class UParticleSystem;
class UParticleSystemComponent;
class ULocalFogVolumeComponent;

UCLASS()
class UNIVERSITYGAME_API ASmokeZone : public AActor
{
	GENERATED_BODY()

public:
	ASmokeZone();

	// is the actor standing in any smoke zone right now?
	static bool IsActorInSmoke(const AActor* Actor);

	// half size of the smoky area (cm); the actor's location is the centre of the floor
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Smoke)
	FVector ZoneExtent = FVector(190.f, 190.f, 140.f);

	// smoke puffs fill the area on a grid with this step (cm)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Smoke)
	float PuffSpacing = 70.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Smoke)
	float PuffScale = 3.4f;

	// < 1 = the smoke moves slower (thick, heavy smoke instead of light steam)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Smoke)
	float SmokeSpeed = 0.4f;

	// sources on the floor and a second, higher layer, so the cloud is dense from the floor to above the head
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Smoke)
	int32 SmokeLayers = 2;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Smoke)
	UParticleSystem* SmokeParticles = nullptr;

	// thick haze filling the whole zone (a local fog volume): how dense it is, and its colour
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Smoke)
	float HazeDensity = 25.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Smoke)
	FLinearColor HazeColor = FLinearColor(0.12f, 0.115f, 0.11f);

protected:
	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Smoke)
	UBoxComponent* Zone;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Smoke)
	ULocalFogVolumeComponent* Haze;

private:
	UPROPERTY(Transient)
	TArray<UParticleSystemComponent*> Puffs;
};
