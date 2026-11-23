// C++ parent of ABP_EnemySoldier: hands the weapon pose computed by the enemy to the animation graph.
// LoweredWeight blends the upper body into A_Guard_RifleLowered (rifle in one hand, barrel down): 1 = lowered,
// 0 = combat pose; in between = the rifle is being raised / lowered. WeaponPitch drives the Aim Offset (AO_Pitch_Hip)
// so the raised rifle follows the player up and down.

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "EnemyAnimInstance.generated.h"

UCLASS()
class UNIVERSITYGAME_API UEnemyAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;

protected:
	// aim offset pitch, degrees (up is positive)
	UPROPERTY(BlueprintReadOnly, Category = "Weapon")
	float WeaponPitch = 0.f;

	// weight of the "rifle lowered" pose on the upper body (Layered blend per bone, Blend Weights 0)
	UPROPERTY(BlueprintReadOnly, Category = "Weapon")
	float LoweredWeight = 0.f;

	// horizontal speed in cm/s - the axis of BS_MM_WalkRun_Guard (relaxed walk with swinging arms)
	UPROPERTY(BlueprintReadOnly, Category = "Weapon")
	float GroundSpeed = 0.f;

	// true while the weapon is up (raised or being raised)
	UPROPERTY(BlueprintReadOnly, Category = "Weapon")
	bool bWeaponRaised = true;
};
