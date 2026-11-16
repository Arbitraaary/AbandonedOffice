#pragma once

#include "CoreMinimal.h"
#include "Camera/CameraModifier.h"
#include "HitCameraModifier.generated.h"

UCLASS()
class UNIVERSITYGAME_API UHitCameraModifier : public UCameraModifier
{
	GENERATED_BODY()

public:
	// FromDirection: world direction from the player towards the shot; Strength 0..1
	void Kick(const FVector& FromDirection, float Strength);

protected:
	virtual bool ModifyCamera(float DeltaTime, FMinimalViewInfo& InOutPOV) override;

private:
	float KickDuration = 0.35f;
	float KickTimeLeft = 0.f;
	float KickStrength = 0.f;
	FRotator KickRotation = FRotator::ZeroRotator;
};
