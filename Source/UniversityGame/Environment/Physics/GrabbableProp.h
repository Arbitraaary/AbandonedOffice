// A prop the player can push by walking into it (character movement physics interaction),
// pick up with E (physics handle - it is carried in front of the camera and still collides with the world),
// put down with E again or throw with the fire button.

#pragma once

#include "CoreMinimal.h"
#include "PhysicsProp.h"
#include "GrabbableProp.generated.h"

UCLASS()
class UNIVERSITYGAME_API AGrabbableProp : public APhysicsProp
{
	GENERATED_BODY()

public:
	AGrabbableProp();

	// speed the prop gets when thrown (cm/s)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float ThrowSpeed = 1000.f;

	virtual void OnGrabbed();

	virtual void OnReleased();

	bool IsHeld() const { return bHeld; }

private:
	bool bHeld = false;
};
