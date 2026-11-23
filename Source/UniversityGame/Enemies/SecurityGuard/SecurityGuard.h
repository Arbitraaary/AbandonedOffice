// Lab 5: the security guard - an NPC enemy on the soldiers' skeleton (own mesh, own rifle, own health bar).
// Movement decisions come from BT_SecurityGuard (ASecurityGuardAIController); this class does what the body does:
// walk/run, aimed bursts, a clearly visible dodge from incoming bullets, hit reactions and death.

#pragma once

#include "CoreMinimal.h"
#include "UniversityGame/Enemies/Enemy.h"
#include "SecurityGuard.generated.h"

class UAnimSequenceBase;
class UAnimMontage;
class UGuardHealthBarWidget;

UCLASS()
class UNIVERSITYGAME_API ASecurityGuard : public AEnemy
{
	GENERATED_BODY()

public:
	ASecurityGuard();

	// ---------------------------------------------------------------- movement
	// walking while searching, running when he sees (or hunts) the player (cm/s)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Movement")
	float WalkSpeed = 170.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Movement")
	float RunSpeed = 420.f;

	// how fast he turns (degrees per second) - turning is always smooth, never snapped
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Movement")
	float TurnRate = 220.f;

	// without patrol points (TargetPoints) he searches random places this far around where he was placed
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Movement")
	float PatrolRadius = 900.f;

	UFUNCTION(BlueprintCallable, Category = Guard)
	void SetRunning(bool bRun);

	UFUNCTION(BlueprintPure, Category = Guard)
	bool IsRunning() const { return bRunning; }

	// next place to walk to while patrolling: the next patrol point, or a random reachable spot near home
	FVector PickPatrolLocation();

	// ---------------------------------------------------------------- combat
	// he shoots only when the player is closer than this (cm)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Combat")
	float AttackRange = 800.f;

	// aim error in degrees (he is a security guard, not a sniper)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Combat")
	float AimSpreadDeg = 3.f;

	// one aimed shot at the target; false if the rifle is not ready (cooldown / reloading)
	bool ShootAt(const AActor* Target);

	float GetFireInterval() const;

	bool IsBusy() const;                      // dodging, staggered or dead - the AI waits

	bool IsDead() const { return IsDying; }

	// ---------------------------------------------------------------- weapon pose (lab 6)
	// while the player is not in range the rifle hangs in the right hand barrel-down (A_Guard_RifleLowered);
	// in range he takes it in both hands and aims (combat pose + aim offset)
	// seconds to raise the rifle when the player comes into range / to lower it again
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Weapon")
	float RaiseTime = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Weapon")
	float LowerTime = 0.6f;

	// on-screen line with what drives the weapon pose (sees / in range / lowered weight / slot montage)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Weapon")
	bool bShowWeaponDebug = false;

	// the rifle is fully up - only then he shoots
	bool IsWeaponReady() const { return WeaponRaiseAlpha > 0.95f; }

	// ---------------------------------------------------------------- obstacles
	// live cables: damage, he freezes and shakes for StunSeconds ("SHOCKED!")
	void Electrocute(float Damage, float StunSeconds, AActor* Source);

	// standing in a smoke zone: he sees nothing and only walks, slowly ("BLINDED")
	bool IsInSmoke() const { return bInSmoke; }

	// short message above the health bar
	void ShowStatus(const FString& Text, const FLinearColor& Color, float Seconds = 1.2f) const;

	// ---------------------------------------------------------------- dodge
	// chance to dodge a bullet grows with the distance it was fired from:
	// MinDodgeChance point-blank ... MaxDodgeChance from DodgeFullDistance and further
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Dodge")
	float MinDodgeChance = 0.1f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Dodge")
	float MaxDodgeChance = 0.85f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Dodge")
	float DodgeFullDistance = 2000.f;

	// sideways jump speed and how long until he can dodge again
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Dodge")
	float DodgeSpeed = 560.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Dodge")
	float DodgeCooldown = 1.2f;

	// prints every dodge decision on screen (distance, chance, roll) - handy for testing and for the report
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Guard|Dodge")
	bool bShowDodgeDebug = false;

	float DodgeChanceForDistance(float Distance) const;

	// ---------------------------------------------------------------- animations (all from AnimStarterPack, played in DefaultSlot)
	UPROPERTY(EditDefaultsOnly, Category = "Guard|Animations")
	TArray<UAnimSequenceBase*> HitReactions;

	UPROPERTY(EditDefaultsOnly, Category = "Guard|Animations")
	TArray<UAnimSequenceBase*> Deaths;

	UPROPERTY(EditDefaultsOnly, Category = "Guard|Animations")
	UAnimSequenceBase* DodgeLeft = nullptr;

	UPROPERTY(EditDefaultsOnly, Category = "Guard|Animations")
	UAnimSequenceBase* DodgeRight = nullptr;

	UPROPERTY(EditDefaultsOnly, Category = "Guard|Animations")
	TArray<UAnimSequenceBase*> LookAroundIdles;

	UPROPERTY(EditDefaultsOnly, Category = "Guard|Animations")
	UAnimSequenceBase* ReloadAnim = nullptr;

	// short "look around" idle animation (used by the look-around task); returns its length
	float PlayLookAroundIdle();

	// ---------------------------------------------------------------- HUD

	virtual void Tick(float DeltaTime) override;

	virtual float TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator,
	                         AActor* DamageCauser) override;

protected:
	virtual void BeginPlay() override;

private:
	void WatchIncomingBullets();
	bool Dodge(const FVector& BulletVelocity, float Chance);
	float FreeSpace(const FVector& Dir, float MaxDistance) const;
	void Die();
	void KeepBodyOutOfWalls();
	void StartReload();
	void FinishReload();
	UAnimMontage* PlayAnim(UAnimSequenceBase* Anim, float Rate = 1.f, float BlendIn = 0.1f, float BlendOut = 0.2f);
	UGuardHealthBarWidget* GetBar() const;
	void AlertController(AActor* Threat) const;
	void UpdateWeaponPose(float DeltaTime);
	float WeaponRaiseAlpha = 0.f;              // 0 = lowered, 1 = raised
	bool bWantedRaised = false;
	// actors the dead body may lie against without being pushed out of them (the automatic glass door)
	UPROPERTY()
	TArray<TObjectPtr<AActor>> BodyPushIgnored;
	bool bBodyPushIgnoredReady = false;

	bool bRunning = false;
	bool bInSmoke = false;
	bool bStunned = false;
	bool bHazardDamage = false;
	float NextSmokeMessage = 0.f;
	float ShakeUntil = 0.f;
	FTimerHandle StunTimer;
	FTimerHandle ShakeTimer;
	bool bReloading = false;
	bool bDeathHandled = false;
	float BusyUntil = 0.f;
	float NextDodgeTime = 0.f;
	FVector Home = FVector::ZeroVector;
	int32 NextPatrolIndex = 0;

	// bullets already judged (each bullet gets one dodge roll)
	TSet<TWeakObjectPtr<AActor>> JudgedBullets;
	TMap<TWeakObjectPtr<AActor>, FVector> LastBulletPos;

	FTimerHandle ReloadTimer;
	FTimerHandle DodgeAnimTimer;
	FVector LastHitDirection = FVector::ForwardVector;
	FTimerHandle DeathPoseTimer;
	float DeathTime = 0.f;
	FVector DeathOrigin = FVector::ZeroVector;
	FVector DeathActorLocation = FVector::ZeroVector;
};
