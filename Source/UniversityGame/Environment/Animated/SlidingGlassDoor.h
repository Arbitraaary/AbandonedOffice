// Automatic sliding glass door of the abandoned office: the sensor still sees you, but the motor is dying.
// When someone (the player or a guard) comes close, the two glass leaves jerk apart, get stuck about half open and shudder;
// when the player walks away they jerk back closed. The motion is a Timeline (UTimelineComponent) with a float curve.

#pragma once

#include "CoreMinimal.h"
#include "Components/TimelineComponent.h"
#include "GameFramework/Actor.h"
#include "SlidingGlassDoor.generated.h"

class UBoxComponent;
class UStaticMeshComponent;
class UMaterialInterface;
class UCurveFloat;

UCLASS()
class UNIVERSITYGAME_API ASlidingGlassDoor : public AActor
{
	GENERATED_BODY()

public:
	ASlidingGlassDoor();

	// opening size (cm); the actor's origin is the middle of the threshold, the leaves slide along its X axis
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Door")
	float DoorWidth = 230.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Door")
	float DoorHeight = 232.f;

	// how far it gets before it sticks (0..1 of fully open)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Door")
	float StuckAt = 0.45f;

	// the leaves' glass and metal frame
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Door")
	UMaterialInterface* GlassMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Door")
	UMaterialInterface* FrameMaterial;

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void Tick(float DeltaTime) override;

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, Category = "Door")
	USceneComponent* LeftLeaf;

	UPROPERTY(VisibleAnywhere, Category = "Door")
	USceneComponent* RightLeaf;

	// the motion sensor: a trigger box in front of and behind the door
	UPROPERTY(VisibleAnywhere, Category = "Door")
	UBoxComponent* Sensor;

	UPROPERTY(VisibleAnywhere, Category = "Door")
	UTimelineComponent* DoorTimeline;

	// 0..1 over 2 s: jerks open, slips back, jerks again, sticks at StuckAt
	UPROPERTY(EditAnywhere, Category = "Door")
	UCurveFloat* OpenCurve;

private:
	UFUNCTION()
	void OnOpenProgress(float Value);

	UFUNCTION()
	void OnSensorBegin(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	                   int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void OnSensorEnd(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex);

	void BuildLeaf(USceneComponent* Leaf, const TArray<UStaticMeshComponent*>& Parts, float Sign);
	void PlaceLeaves();
	bool IsPlayer(const AActor* Actor) const;          // any living pawn (kept name: player or guard)
	int32 CountPeopleInside() const;

	UPROPERTY()
	TArray<UStaticMeshComponent*> LeftParts;

	UPROPERTY()
	TArray<UStaticMeshComponent*> RightParts;

	float OpenAmount = 0.f;            // from the timeline, 0..1
	float Shudder = 0.f;               // the motor straining while stuck
	float NextShudder = 0.f;
	int32 PlayersInside = 0;
};
