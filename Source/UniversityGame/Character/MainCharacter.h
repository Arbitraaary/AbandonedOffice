// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GenericTeamAgentInterface.h"
#include "UniversityGame/Core/PlayersTeam.h"
#include "EnhancedInputComponent.h"
#include "Controllers/ActivePlayerController.h"
#include "UniversityGame/Weapons/Bullet.h"
#include "MainCharacter.generated.h"

class ABaseWeapon;
class UCameraComponent;
class USpringArmComponent;
class UAnimMontage;
class UInputMappingContext;
class UInputAction;
class UPhysicsHandleComponent;
class AGrabbableProp;
class FPickupMessageOverlay;

UCLASS()
class UNIVERSITYGAME_API AMainCharacter : public ACharacter, public IGenericTeamAgentInterface
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
	// first-person camera in the head (also used for aiming down the sights and for picking things up)
	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = Camera)
	UCameraComponent* CameraComponent;

	// third-person view: a camera on a spring arm over the right shoulder, so the character's animations are visible
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Camera)
	USpringArmComponent* CameraBoom;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Camera)
	UCameraComponent* ThirdPersonCamera;

	// the game starts in the first-person view; V switches to a free third-person camera that orbits the character
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Camera)
	bool bThirdPerson = false;

	// V: third person <-> first person (the key is mapped in code, no input asset needed)
	UPROPERTY()
	UInputAction* ToggleViewAction;

	UPROPERTY()
	UInputMappingContext* ViewMappingContext;

	void ToggleView(const FInputActionValue& Value);

	// switches the active camera: third person unless aiming down the sights or in first person
	void UpdateActiveCamera();

	// the camera the player is looking through right now
	UCameraComponent* GetViewCamera() const;

	// turns the body to the camera's yaw (used before a shot in third person)
	void FaceViewDirection();

	// hides the editor's camera models so they never appear in the game
	void HideCameraModels() const;
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

	// reload montage in three sections: "Start" (weapon goes down), "Loop" (rounds go in, repeats itself),
	// "End" (weapon comes back up). The Loop section carries the Reload Cycle notify.
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = Weapon)
	UAnimMontage* ReloadMontage;

	// rounds loaded per cycle of the Loop section
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = Weapon)
	int32 RoundsPerReloadCycle = 10;

	UPROPERTY(BlueprintReadOnly, Category = Weapon)
	bool bIsReloading = false;

	UFUNCTION()
	void OnReloadMontageEnded(UAnimMontage* Montage, bool bInterrupted);

	void UpdateAmmoHUD() const;
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
	// the player belongs to PlayersTeam - AI controllers treat this team as hostile
	virtual FGenericTeamId GetGenericTeamId() const override { return FPlayersTeam(); }

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

public:
	// called by the Reload Cycle notify once per Loop cycle: loads a few rounds, finishes when the magazine is full
	void OnReloadCycle();

	// called by the Magazine Out notify: the left hand pulls the magazine out of the weapon
	void OnMagazineOut();
};
