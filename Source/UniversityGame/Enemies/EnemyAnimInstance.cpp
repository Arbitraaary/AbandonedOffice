#include "EnemyAnimInstance.h"

#include "Enemy.h"

void UEnemyAnimInstance::NativeUpdateAnimation(const float DeltaSeconds)
{
	Super::NativeUpdateAnimation(DeltaSeconds);
	if (const AEnemy* Enemy = Cast<AEnemy>(TryGetPawnOwner()))
	{
		WeaponPitch = Enemy->GetWeaponAimPitch();
		bWeaponRaised = Enemy->IsWeaponRaised();
		LoweredWeight = Enemy->GetWeaponLoweredWeight();
		GroundSpeed = Enemy->GetVelocity().Size2D();
	}
}
