// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "EnhancedInputComponent.h"
#include "Controllers/ActivePlayerController.h"
#include "UniversityGame/Weapons/Bullet.h"
#include "MainCharacter.generated.h"

class ABaseWeapon;
class UCameraComponent;
class UInputMappingContext;
class UInputAction;
class UPhysicsHandleComponent;
class AGrabbableProp;
class FPickupMessageOverlay;

UCLASS()
class UNIVERSITYGAME_API AMainCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	// Sets default values for this character's properties
	AMainCharacter();

protected:
	// Called when the game starts or when spawned
	virtual void BeginPlay() override;

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY()
	AActivePlayerController* PlayerController;

	// CAMERA BEGIN
	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = Camera)
	UCameraComponent* CameraComponent;
	// CAMERA END

	// MOVEMENT BEGIN
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Movement)
	double Speed = 45;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Movement)
	double MaxScopedSpeed = 27;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Movement)
	double MaxCrouchSpeed = 20;

	UPROPERTY(BlueprintReadWrite)
	bool ScopeButtonDown = false;

	UPROPERTY(BlueprintReadWrite)
	bool CanMove = true;
	
	void Move(const FInputActionValue& Value);

	void Look(const FInputActionValue& Value);

	void CustomCrouch(const FInputActionValue& Value);
	
	void Scope(const FInputActionValue& Value);
	// MOVEMENT END

	// INPUT BEGIN
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Input)
	UInputAction* MovementAction;
	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Input)
	UInputAction* LookAction;
	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Input)
	UInputAction* JumpAction;
	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Input)
	UInputAction* CrouchAction;
	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Input)
	UInputAction* ScopeAction;
	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Input)
	UInputAction* FireAction;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category=Input)
	UInputAction* ReloadAction;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category=Input)
	UInputAction* PickAction;
	// INPUT END

	// Shooting BEGIN
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Weapon)
	TSubclassOf<ABaseWeapon>  WeaponClass;

	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = Weapon)
	bool CanShoot = true;

	UPROPERTY()
	ABaseWeapon* Weapon;
	
	void Fire(const FInputActionValue& Value);

	UFUNCTION()
	void Reload(const FInputActionValue& Value);

	UFUNCTION(BlueprintImplementableEvent)
	void OnReload();
	// Shooting END

	// Damage START
	UFUNCTION(BlueprintImplementableEvent)
	void OnBeingShot();

	UPROPERTY(BlueprintReadWrite)
	bool CanPlayShotAnim = true;
	// Damage END

	void Pick(const FInputActionValue& Value);

	void DropWeapon();

	ABaseWeapon* AcquireWeapon(UClass* NewWeaponClass, const ABaseWeapon* NewWeapon = nullptr);

	void OnInvincibilityFinished();

	// PHYSICS INTERACTION BEGIN
	// E on a box / bin / cone picks it up (physics handle), E again puts it down, fire throws it
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Physics)
	UPhysicsHandleComponent* PhysicsHandle;

	UPROPERTY()
	AGrabbableProp* HeldProp = nullptr;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float GrabDistance = 250.f;

	// where a carried prop is held, relative to the camera: X forward, Y right, Z up (cm, pitch ignored) -
	// a bit to the left, low and close, as if carried under the arm
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	FVector HoldOffset = FVector(70.f, -38.f, -55.f);

	// yaw of the prop relative to the view when it was picked up (it keeps that while carried)
	float HeldYawOffset = 0.f;

	// loose papers within this radius of the feet get blown along when walking
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float PaperKickRadius = 75.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float PaperKickMinSpeed = 60.f;

	bool TryGrabProp();

	void ReleaseProp(bool bThrow);

	void UpdateHeldProp();

	void KickLoosePapers();

	TSharedPtr<FPickupMessageOverlay> PickupMessages;

	// one handle for the bulletproof timer: picking up another vest restarts it instead of the old timer ending it early
	FTimerHandle InvincibilityTimerHandle;

	float LastPickTime = -100.f;
	float FireBlockedUntil = -100.f;
	// PHYSICS INTERACTION END

private:
	UPROPERTY(EditAnywhere, Category = Health)
	float Health;
	
	UPROPERTY(EditAnywhere, Category = Health)
	float MaxHealth = 100.f;

	UPROPERTY(EditDefaultsOnly, Category = Health)
	bool bIsInvincible = false;
	
	virtual float TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser) override;

	float ChangeHealth(float NewHealth);
	
public:	
	// Called every frame
	virtual void Tick(float DeltaTime) override;

	// Called to bind functionality to input
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	
	// returns how much health was actually restored (0 = already full)
	float Heal(float AdditionalHealth);

	// returns how many rounds were actually added (0 = reserve already full)
	int GetAmmo(int AdditionalAmmo);

	// short text under the crosshair: "+15 HEALTH", "+15 AMMO", "BULLETPROOF FOR 15 S" ...
	void ShowPickupMessage(const FText& Text, const FLinearColor& Color, float Seconds = 2.5f);

	void MakeInvincibleFor(float Seconds);

	void TeleportToLocation(FVector Location);
};
