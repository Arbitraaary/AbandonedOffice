#include "HitCameraModifier.h"

#include "Camera/CameraTypes.h"
#include "Camera/PlayerCameraManager.h"

void UHitCameraModifier::Kick(const FVector& FromDirection, const float Strength)
{
	FRotator ViewRot = FRotator::ZeroRotator;
	if (CameraOwner)
	{
		ViewRot = CameraOwner->GetCameraRotation();
	}
	// where the shot came from in view space: Y > 0 - from the right, X < 0 - from behind
	const FVector Local = ViewRot.UnrotateVector(FromDirection.GetSafeNormal());
	const float Side = FMath::Abs(Local.Y) > 0.15f ? FMath::Sign(Local.Y) : (FMath::RandBool() ? 1.f : -1.f);

	KickStrength = FMath::Clamp(Strength, 0.f, 1.f);
	KickRotation = FRotator(2.5f + (Local.X < 0.f ? 1.f : 0.f),     // pitch: the head jerks up
	                        -Side * 3.f,                           // yaw: away from the shot
	                        Side * 4.f);                           // roll: tilts with the hit
	KickTimeLeft = KickDuration;
}

bool UHitCameraModifier::ModifyCamera(const float DeltaTime, FMinimalViewInfo& InOutPOV)
{
	Super::ModifyCamera(DeltaTime, InOutPOV);
	if (KickTimeLeft <= 0.f)
	{
		return false;
	}
	KickTimeLeft = FMath::Max(KickTimeLeft - DeltaTime, 0.f);
	const float Fade = KickTimeLeft / KickDuration;              // 1 right after the hit -> 0
	const float Envelope = Fade * Fade * KickStrength;
	const float Wobble = FMath::Sin((KickDuration - KickTimeLeft) * 55.f) * 0.6f;

	InOutPOV.Rotation = InOutPOV.Rotation + FRotator(KickRotation.Pitch * Envelope + Wobble * Envelope,
	                              KickRotation.Yaw * Envelope,
	                              KickRotation.Roll * Envelope);
	return false;
}
