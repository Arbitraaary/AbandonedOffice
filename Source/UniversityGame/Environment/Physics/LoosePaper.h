// A loose A4 sheet lying on the floor. It simulates as a thin box (its own collision body, so it works whatever
// collision the paper mesh has). Very light, strong air drag. When a character steps on / next to it, the sheet is
// blown along the floor:
//   * the character's capsule overlaps the sheet  -> NotifyActorBeginOverlap -> BlowAway
//   * every frame the player also blows sheets around the feet (AMainCharacter::KickLoosePapers)
// Characters never get blocked by paper and the camera never shakes.

#pragma once

#include "CoreMinimal.h"
#include "PhysicsProp.h"
#include "LoosePaper.generated.h"

class UBoxComponent;

UCLASS()
class UNIVERSITYGAME_API ALoosePaper : public APhysicsProp
{
	GENERATED_BODY()

public:
	ALoosePaper();

	virtual UPrimitiveComponent* GetPhysicsBody() const override;

	// WalkerVelocity - velocity of whoever walks by; Strength01 - 0..1 (distance and speed already applied)
	void BlowAway(const FVector& WalkerVelocity, float Strength01);

	virtual void NotifyActorBeginOverlap(AActor* OtherActor) override;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Physics)
	UBoxComponent* PaperBody;

	// horizontal speed change at Strength 0 / 1 (cm/s)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float MinPush = 80.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float MaxPush = 240.f;

	// how much the sheet lifts off the floor (cm/s)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float Lift = 110.f;

	// random spin (deg/s)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float Spin = 400.f;

	// a sheet reacts at most once per this many seconds
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float Cooldown = 0.25f;

private:
	float LastBlowTime = -100.f;
};
