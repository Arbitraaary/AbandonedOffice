// Obstacle for the security guard: live cables torn out of the ceiling hang down to the floor and spark.
// A guard who walks into them gets an electric shock: damage, he freezes and shakes for a moment.
// The sparks are tiny glowing streaks simulated here (bursts from the bare copper ends) + a flickering light.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparkingCables.generated.h"

class UBoxComponent;
class UInstancedStaticMeshComponent;
class UPointLightComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;

UCLASS()
class UNIVERSITYGAME_API ASparkingCables : public AActor
{
	GENERATED_BODY()

public:
	ASparkingCables();

	virtual void Tick(float DeltaSeconds) override;

	// height of the ceiling above the floor (cm): the actor sits at the ceiling, the cables reach the floor
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Cables)
	float CeilingHeight = 390.f;

	// shock: damage to the guard, how long he is stunned, and how often it can repeat while he stays inside
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Cables)
	float ShockDamage = 15.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Cables)
	float StunTime = 1.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Cables)
	float ShockCooldown = 2.5f;

	// seconds between spark bursts (random in this range)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Sparks)
	FVector2D BurstInterval = FVector2D(0.35f, 1.6f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Sparks)
	UMaterialInterface* SparkMaterial = nullptr;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Cables)
	UStaticMeshComponent* Cables;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Cables)
	UBoxComponent* ShockZone;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Sparks)
	UInstancedStaticMeshComponent* Sparks;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Sparks)
	UPointLightComponent* Flash;

protected:
	virtual void BeginPlay() override;
	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void NotifyActorBeginOverlap(AActor* OtherActor) override;

private:
	struct FSpark
	{
		FVector Pos;
		FVector Vel;
		float Life;
		float MaxLife;
	};

	void Burst(const FVector& Where, int32 Count, float Speed);
	void ShockOverlappingGuards();
	FVector RandomSparkPoint() const;

	TArray<FSpark> Live;
	TArray<FVector> SparkPoints;            // world positions of the copper ends (mesh sockets Spark_*)
	float NextBurst = 0.f;
	float FlashLevel = 0.f;
	float FloorZ = 0.f;
	TMap<TWeakObjectPtr<AActor>, float> LastShock;
};
