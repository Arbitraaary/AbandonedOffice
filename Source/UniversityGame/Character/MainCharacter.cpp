// Fill out your copyright notice in the Description page of Project Settings.


#include "MainCharacter.h"

#include "EnhancedInputSubsystems.h"
#include "KismetTraceUtils.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputCoreTypes.h"
#include "Kismet/KismetMathLibrary.h"
#include "Components/InputComponent.h"
#include "GameFramework/PawnMovementComponent.h"
#include "ProfilingDebugging/CookStats.h"
#include "UniversityGame/Weapons/BaseWeapon.h"
#include "UniversityGame/Environment/Physics/GrabbableProp.h"
#include "UniversityGame/Environment/Physics/LoosePaper.h"
#include "Components/CapsuleComponent.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "PhysicsEngine/PhysicsHandleComponent.h"
#include "UniversityGame/HUD/PickupMessageOverlay.h"

// Sets default values
AMainCharacter::AMainCharacter()
{
 	// Set this character to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;
	SetCanBeDamaged(true);
	
	// Camera
	CameraComponent = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
	check(CameraComponent != nullptr);
	CameraComponent->SetupAttachment(GetMesh(), TEXT("head"));
	CameraComponent->bUsePawnControlRotation = true;

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 300.f;
	CameraBoom->SocketOffset = FVector(0.f, 0.f, 40.f);      // centred on the character, so it can be seen from every side
	CameraBoom->bUsePawnControlRotation = true;
	CameraBoom->bDoCollisionTest = true;                      // pulls in instead of going through walls
	CameraBoom->ProbeSize = 12.f;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 18.f;

	ThirdPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("ThirdPersonCamera"));
	ThirdPersonCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	ThirdPersonCamera->bUsePawnControlRotation = false;

#if WITH_EDITORONLY_DATA
	// the grey camera model the editor draws for camera components must never show up in the game
	CameraComponent->bCameraMeshHiddenInGame = true;
	ThirdPersonCamera->bCameraMeshHiddenInGame = true;
#endif

	// Movement
	if (ACharacter::GetMovementComponent())
	{
		ACharacter::GetMovementComponent()->GetNavAgentPropertiesRef().bCanCrouch = true;
	}

	// Physics interaction: walking into a physics prop pushes it, E grabs it
	if (UCharacterMovementComponent* CharacterMovementComponent = GetCharacterMovement())
	{
		CharacterMovementComponent->bEnablePhysicsInteraction = true;
		CharacterMovementComponent->PushForceFactor = 150000.f;
		CharacterMovementComponent->InitialPushForceFactor = 200.f;
		CharacterMovementComponent->bScalePushForceToVelocity = true;
	}
	PhysicsHandle = CreateDefaultSubobject<UPhysicsHandleComponent>(TEXT("PhysicsHandle"));
	PhysicsHandle->LinearStiffness = 1500.f;
	PhysicsHandle->LinearDamping = 120.f;
	PhysicsHandle->AngularStiffness = 1000.f;
	PhysicsHandle->AngularDamping = 300.f;
	PhysicsHandle->InterpolationSpeed = 25.f;

	Health = MaxHealth;
}

// Called when the game starts or when spawned
void AMainCharacter::BeginPlay()
{
	Super::BeginPlay();

	if (PlayerController = Cast<AActivePlayerController>(GetController()), PlayerController == nullptr)
	{
		if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(INDEX_NONE, 5.f, FColor::Red, TEXT("Could not cast to AActivePlayerController"));
		}
	}

	ScopeButtonDown = false;
	CanMove = true;
	HideCameraModels();
	UpdateActiveCamera();

	AcquireWeapon(WeaponClass);
	ChangeHealth(MaxHealth);
}

void AMainCharacter::Move(const FInputActionValue& Value)
{
	if (!CanMove) return;

	const UPawnMovementComponent* MovementComponent = GetMovementComponent();
	if (MovementComponent == nullptr) return;
	
	const FVector2D MovementVector = Value.Get<FVector2D>();

	const FVector MovementMath = FVector(MovementVector.Y, MovementVector.X, 0.f);
	const FRotator Rotation = Controller->GetControlRotation();
	const FRotator YawRotation = FRotator(0, Rotation.Yaw, 0);

	const FVector Vector = UKismetMathLibrary::Normal(FRotationMatrix(YawRotation).TransformVector(MovementMath));
	const double SpeedModifier = MovementComponent->IsCrouching()
		? UKismetMathLibrary::Clamp(Speed, 0, MaxCrouchSpeed)
		: ScopeButtonDown
			? UKismetMathLibrary::Clamp(Speed, 0, MaxScopedSpeed)
			: Speed;
	
	AddMovementInput(Vector * SpeedModifier * GetWorld()->GetDeltaSeconds());
}

void AMainCharacter::Look(const FInputActionValue& Value)
{
	const FVector2D LookAxisVector = Value.Get<FVector2D>();
	
	AddControllerPitchInput(LookAxisVector.Y);
	AddControllerYawInput(LookAxisVector.X);
}

void AMainCharacter::CustomCrouch(const FInputActionValue& Value)
{
	if (Value.Get<bool>())
	{
		Crouch();
	}else
	{
		UnCrouch();
	}
}

void AMainCharacter::Scope(const FInputActionValue& Value)
{
	if (const bool NewValue = Value.Get<bool>(); ScopeButtonDown != NewValue)
	{
		ScopeButtonDown = NewValue;
		UpdateActiveCamera();
		if (ScopeButtonDown)
		{
			PlayerController->HideCrosshair();
		}else
		{
			PlayerController->ShowCrosshair();
		}
	}
}

void AMainCharacter::Fire(const FInputActionValue& Value)
{
	// carrying a prop: the fire button throws it instead of shooting
	if (HeldProp != nullptr)
	{
		ReleaseProp(true);
		FireBlockedUntil = GetWorld()->GetTimeSeconds() + 0.4f;
		return;
	}
	if (GetWorld()->GetTimeSeconds() < FireBlockedUntil) return;

	if (WeaponClass == nullptr) return;
	if (!CanShoot) return;

	// orbiting camera: the character turns to where the camera looks before shooting
	if (bThirdPerson && !ScopeButtonDown)
	{
		FaceViewDirection();
	}

	// aim from the camera the player looks through: the bullet goes where the centre of the screen points
	const UCameraComponent* ViewCamera = GetViewCamera();
	const FVector CameraLocation = ViewCamera->GetComponentLocation();
	const FVector CameraDirection = ViewCamera->GetForwardVector();

	const FVector MuzzleLocation = Weapon->GetMuzzleLocation();
	const FVector SightLocation = Weapon->GetSightLocation();
	float TraceDistance = 10000.f;

	FVector TraceDirection;

	if (ScopeButtonDown)
	{
		TraceDirection = SightLocation - CameraLocation;
	}else
	{
		TraceDirection = CameraDirection;
	}
	TraceDirection.Normalize();
	TraceDirection *= TraceDistance;
	
	FCollisionQueryParams RV_TraceParams = FCollisionQueryParams(FName(TEXT("RV_Trace")), true, this);
	RV_TraceParams.bTraceComplex = true;
	RV_TraceParams.bReturnPhysicalMaterial = false;
	
	FHitResult RV_Hit;
	
	GetWorld()->LineTraceSingleByChannel(RV_Hit, CameraLocation, CameraLocation + TraceDirection, ECC_Visibility, RV_TraceParams);

	FVector LaunchDirection;
	if (RV_Hit.bBlockingHit)
	{
		LaunchDirection = UKismetMathLibrary::Normal(RV_Hit.ImpactPoint - MuzzleLocation);
	}else
	{
		LaunchDirection = UKismetMathLibrary::Normal(CameraLocation + TraceDirection - MuzzleLocation);
	}
	Weapon->Fire(LaunchDirection.Rotation(), LaunchDirection);

	PlayerController->UpdateUnequippedAmmoCount(Weapon->GetUnequippedAmmoCount());
	PlayerController->UpdateAmmoInMagCount(Weapon->GetMagazineAmmoCount());

	// no bullets left at all -> game over
	if (Weapon->GetMagazineAmmoCount() <= 0 && Weapon->GetUnequippedAmmoCount() <= 0)
	{
		PlayerController->ShowGameOver(FText::FromString(TEXT("You are out of ammo")));
	}
}

void AMainCharacter::Reload(const FInputActionValue& Value)
{
	if (!Weapon || bIsReloading || !Weapon->CanReload()) return;

	UAnimInstance* Anim = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	if (!ReloadMontage || !Anim)
	{
		// no montage set: the old instant reload
		CanShoot = false;
		Weapon->Reload();
		OnReload();
		UpdateAmmoHUD();
		return;
	}

	// Start (weapon down) -> Loop (rounds in, repeats; each cycle calls OnReloadCycle) -> End (weapon up)
	if (Anim->Montage_Play(ReloadMontage) <= 0.f) return;
	bIsReloading = true;
	CanShoot = false;
	FOnMontageEnded EndDelegate;
	EndDelegate.BindUObject(this, &AMainCharacter::OnReloadMontageEnded);
	Anim->Montage_SetEndDelegate(EndDelegate, ReloadMontage);
}

void AMainCharacter::OnReloadCycle()
{
	if (!bIsReloading || !Weapon) return;
	Weapon->MagazineIn();                          // the magazine from the hand goes back into the weapon
	Weapon->ReloadRounds(RoundsPerReloadCycle);
	UpdateAmmoHUD();

	// magazine full (or no rounds left): leave the loop and raise the weapon
	if (!Weapon->CanReload())
	{
		if (UAnimInstance* Anim = GetMesh()->GetAnimInstance())
		{
			Anim->Montage_JumpToSection(TEXT("End"), ReloadMontage);
		}
	}
}

void AMainCharacter::OnReloadMontageEnded(UAnimMontage* Montage, bool bInterrupted)
{
	// interrupted (e.g. by a hit reaction): the rounds already loaded stay, R starts the reload again
	bIsReloading = false;
	CanShoot = true;
	if (Weapon)
	{
		Weapon->MagazineIn();                      // never leave the magazine in the hand
	}
	UpdateAmmoHUD();
}

void AMainCharacter::OnMagazineOut()
{
	if (bIsReloading && Weapon)
	{
		Weapon->MagazineOut(GetMesh());
	}
}

void AMainCharacter::UpdateAmmoHUD() const
{
	if (!PlayerController || !Weapon) return;
	PlayerController->UpdateUnequippedAmmoCount(Weapon->GetUnequippedAmmoCount());
	PlayerController->UpdateAmmoInMagCount(Weapon->GetMagazineAmmoCount());
}

void AMainCharacter::Pick(const FInputActionValue& Value)
{
	// E fires every frame while held - react once per press
	const float Now = GetWorld()->GetTimeSeconds();
	if (Now - LastPickTime < 0.3f)
	{
		LastPickTime = Now;
		return;
	}
	LastPickTime = Now;

	// already carrying something -> put it down
	if (HeldProp != nullptr)
	{
		ReleaseProp(false);
		return;
	}

	const FVector CameraLocation = CameraComponent->GetComponentLocation();
	const FVector CameraDirection = CameraComponent->GetForwardVector();
	
	FCollisionObjectQueryParams RV_ObjectQueryParams = FCollisionObjectQueryParams(
		ECC_TO_BITFIELD(ECC_GameTraceChannel2)
	);
	
	FCollisionQueryParams RV_TraceParams = FCollisionQueryParams(FName(TEXT("RV_Trace")), true, this);
	RV_TraceParams.bReturnPhysicalMaterial = false;
	RV_TraceParams.bDebugQuery = true;

	FCollisionShape RV_TraceShape;
	RV_TraceShape.SetSphere(50.f);
	
	FHitResult RV_Hit;
	GetWorld()->SweepSingleByObjectType(RV_Hit, CameraLocation, CameraLocation + CameraDirection * 100.f, FQuat::Identity, RV_ObjectQueryParams, RV_TraceShape, RV_TraceParams);

	FHitResult DebugHit;
	FLinearColor DebugTraceColor = FLinearColor::Green;
	FLinearColor DebugHitColor = FLinearColor::Red;
	DrawDebugSphereTraceSingle(GetWorld(), CameraLocation, CameraLocation + CameraDirection * 100.f, 50.f, EDrawDebugTrace::ForOneFrame, true, DebugHit, DebugTraceColor, DebugHitColor, 3.f);

	
	AActor* HitActor = RV_Hit.GetActor();
	if (ABaseWeapon* HitWeapon = Cast<ABaseWeapon>(HitActor); HitWeapon != nullptr)
	{
		if (Weapon != nullptr)
		{
			DropWeapon();
		}
		AcquireWeapon(HitWeapon->GetClass(), HitWeapon);
		HitWeapon->Destroy();
		return;
	}

	// no weapon in front of us -> try to pick up a physics prop (box, bin, cone)
	TryGrabProp();
}

bool AMainCharacter::TryGrabProp()
{
	const FVector Start = CameraComponent->GetComponentLocation();
	const FVector End = Start + CameraComponent->GetForwardVector() * GrabDistance;

	FCollisionQueryParams Params(FName(TEXT("GrabTrace")), false, this);
	if (Weapon != nullptr)
	{
		Params.AddIgnoredActor(Weapon);
	}

	FHitResult Hit;
	if (!GetWorld()->SweepSingleByChannel(Hit, Start, End, FQuat::Identity, ECC_Visibility, FCollisionShape::MakeSphere(12.f), Params))
	{
		return false;
	}

	AGrabbableProp* Prop = Cast<AGrabbableProp>(Hit.GetActor());
	if (Prop == nullptr) return false;

	UPrimitiveComponent* PropComponent = Prop->GetMesh();
	Prop->OnGrabbed();
	PhysicsHandle->GrabComponentAtLocationWithRotation(PropComponent, NAME_None, PropComponent->GetCenterOfMass(), PropComponent->GetComponentRotation());
	HeldYawOffset = FRotator::NormalizeAxis(PropComponent->GetComponentRotation().Yaw - GetControlRotation().Yaw);
	HeldProp = Prop;
	return true;
}

void AMainCharacter::ReleaseProp(const bool bThrow)
{
	if (HeldProp == nullptr) return;

	PhysicsHandle->ReleaseComponent();
	HeldProp->OnReleased();
	if (bThrow)
	{
		HeldProp->GetMesh()->AddImpulse(CameraComponent->GetForwardVector() * HeldProp->ThrowSpeed + GetVelocity(), NAME_None, true);
	}
	HeldProp = nullptr;
}

void AMainCharacter::UpdateHeldProp()
{
	if (HeldProp == nullptr) return;
	if (!IsValid(HeldProp))
	{
		HeldProp = nullptr;
		return;
	}

	// under the arm: offset from the camera along the horizontal view direction, so looking up / down doesn't swing it
	const FRotator YawOnly(0.f, GetControlRotation().Yaw, 0.f);
	const FVector Target = CameraComponent->GetComponentLocation() + YawOnly.RotateVector(HoldOffset);
	PhysicsHandle->SetTargetLocationAndRotation(Target, FRotator(0.f, YawOnly.Yaw + HeldYawOffset, 0.f));

	// stuck behind a wall / desk -> let it go
	if (FVector::Dist(HeldProp->GetActorLocation(), Target) > GrabDistance)
	{
		ReleaseProp(false);
	}
}

void AMainCharacter::KickLoosePapers()
{
	const FVector Velocity = GetVelocity();
	const float Speed2D = Velocity.Size2D();
	if (Speed2D < PaperKickMinSpeed) return;

	const FVector Feet = GetActorLocation() - FVector(0.f, 0.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight());

	TArray<FOverlapResult> Overlaps;
	const FCollisionObjectQueryParams ObjectParams(FCollisionObjectQueryParams::AllDynamicObjects);
	const FCollisionQueryParams Params(FName(TEXT("PaperKick")), false, this);
	GetWorld()->OverlapMultiByObjectType(Overlaps, Feet + FVector(0.f, 0.f, 15.f), FQuat::Identity, ObjectParams,
		FCollisionShape::MakeSphere(PaperKickRadius), Params);

	const float SpeedFactor = FMath::Clamp(Speed2D / 600.f, 0.25f, 1.f);
	for (const FOverlapResult& Overlap : Overlaps)
	{
		if (ALoosePaper* Paper = Cast<ALoosePaper>(Overlap.GetActor()))
		{
			const float Distance = FVector::Dist2D(Paper->GetActorLocation(), Feet);
			const float Closeness = 1.f - FMath::Clamp(Distance / PaperKickRadius, 0.f, 1.f);
			Paper->BlowAway(Velocity, SpeedFactor * (0.35f + 0.65f * Closeness));
		}
	}
}

void AMainCharacter::DropWeapon()
{
	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
	const FTransform WeaponTransform = Weapon->GetActorTransform();

	if (ABaseWeapon* DroppedWeapon = Cast<ABaseWeapon>(GetWorld()->SpawnActor(WeaponClass, &WeaponTransform, SpawnParams));
		DroppedWeapon != nullptr
	)
	{
		DroppedWeapon->SkeletalMeshComponent->SetSimulatePhysics(true);
		DroppedWeapon->CopyFrom(Weapon);
	
		Weapon->Destroy();
		Weapon = nullptr;
	}
}

ABaseWeapon* AMainCharacter::AcquireWeapon(UClass* NewWeaponClass, const ABaseWeapon* NewWeapon)
{
	FActorSpawnParameters SpawnParams;
	SpawnParams.Owner = this;
	SpawnParams.Instigator = GetInstigator();
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

	if(Weapon = GetWorld()->SpawnActor<ABaseWeapon>(
			NewWeaponClass,
			FVector(0.f, 0.f, 0.f),
			FRotator(0.f, 0.f, 0.f),
			SpawnParams
		);
		Weapon!= nullptr
	)
	{
		Weapon->SetActorEnableCollision(false);
		Weapon->AttachToComponent(GetMesh(), FAttachmentTransformRules(EAttachmentRule::SnapToTarget, true), Weapon->GetSocketName());

		if (NewWeapon != nullptr)
		{
			Weapon->CopyFrom(NewWeapon);
		}
		Weapon->SetInfiniteAmmo(false);
		WeaponClass = NewWeaponClass;
		
		PlayerController->UpdateMagCapacity(Weapon->GetMagazineAmmoCapacity());
		PlayerController->UpdateAmmoInMagCount(Weapon->GetMagazineAmmoCount());
		PlayerController->UpdateGeneralAmmoCapacity(Weapon->GetGeneralAmmoCapacity());
		PlayerController->UpdateUnequippedAmmoCount(Weapon->GetUnequippedAmmoCount());

		return Weapon;
	}
	return nullptr;
}

// Called every frame
void AMainCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	UpdateHeldProp();
	KickLoosePapers();
}

// Called to bind functionality to input
void AMainCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	
	if (UEnhancedInputComponent* Input = CastChecked<UEnhancedInputComponent>(PlayerInputComponent))
	{
		Input->BindAction(MovementAction, ETriggerEvent::Triggered, this, &AMainCharacter::Move);
		Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AMainCharacter::Look);
		Input->BindAction(JumpAction, ETriggerEvent::Triggered, this, &AMainCharacter::Jump);
		Input->BindAction(CrouchAction, ETriggerEvent::Triggered, this, &AMainCharacter::CustomCrouch);
		Input->BindAction(ScopeAction, ETriggerEvent::Triggered, this, &AMainCharacter::Scope);
		Input->BindAction(FireAction, ETriggerEvent::Triggered, this, &AMainCharacter::Fire);
		Input->BindAction(ReloadAction, ETriggerEvent::Triggered, this, &AMainCharacter::Reload);
		Input->BindAction(PickAction, ETriggerEvent::Triggered, this, &AMainCharacter::Pick);

		// V toggles the view; the action and its key are created here, on top of the project's mapping context
		if (!ToggleViewAction)
		{
			ToggleViewAction = NewObject<UInputAction>(this);
			ToggleViewAction->ValueType = EInputActionValueType::Boolean;
			ViewMappingContext = NewObject<UInputMappingContext>(this);
			ViewMappingContext->MapKey(ToggleViewAction, EKeys::V);
		}
		if (const APlayerController* PC = Cast<APlayerController>(GetController()))
		{
			if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
			{
				Subsystem->AddMappingContext(ViewMappingContext, 1);
			}
		}
		Input->BindAction(ToggleViewAction, ETriggerEvent::Started, this, &AMainCharacter::ToggleView);
	}

}

float AMainCharacter::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator,
                                 AActor* DamageCauser)
{
	if (!bIsInvincible)
	{
		ChangeHealth(Health - DamageAmount);

		if (PlayerController && DamageAmount > 0.f)
		{
			// where the shot came from: back along the bullet's flight, else the shooter, else the bullet itself
			FVector From = GetActorLocation() + GetActorForwardVector() * 100.f;
			if (DamageCauser && !DamageCauser->GetVelocity().IsNearlyZero())
			{
				From = DamageCauser->GetActorLocation() - DamageCauser->GetVelocity().GetSafeNormal() * 500.f;
			}
			else if (EventInstigator && EventInstigator->GetPawn())
			{
				From = EventInstigator->GetPawn()->GetActorLocation();
			}
			else if (DamageCauser)
			{
				From = DamageCauser->GetActorLocation();
			}
			PlayerController->PlayHitReaction(From, DamageAmount);
		}
	}
	
	UE_LOG(LogTemp, Warning, TEXT("%s has %f amount of health left. Instigator controller: %s"), *GetName(), Health, *GetNameSafe(EventInstigator));

	if (CanPlayShotAnim)
	{
		CanPlayShotAnim = false;
		OnBeingShot();
	}
	
	return DamageAmount;
}

float AMainCharacter::ChangeHealth(const float NewHealth)
{
	Health = FMath::Clamp(NewHealth, 0, MaxHealth);
	
	PlayerController->UpdateHealthPercentage(Health/MaxHealth);
	if (Health <= 0.f)
	{
		PlayerController->ShowGameOver(FText::FromString(TEXT("You have no health left")));
	}
	return Health;
}

int AMainCharacter::GetAmmo(const int AdditionalAmmo)
{
	if (Weapon == nullptr) return 0;

	const int Before = Weapon->GetUnequippedAmmoCount();
	Weapon->AddAmmo(AdditionalAmmo);
	const int Added = Weapon->GetUnequippedAmmoCount() - Before;

	PlayerController->UpdateAmmoInMagCount(Weapon->GetMagazineAmmoCount());
	PlayerController->UpdateUnequippedAmmoCount(Weapon->GetUnequippedAmmoCount());
	return Added;
}

void AMainCharacter::ShowPickupMessage(const FText& Text, const FLinearColor& Color, const float Seconds)
{
	if (!IsLocallyControlled()) return;
	if (!PickupMessages.IsValid())
	{
		PickupMessages = MakeShared<FPickupMessageOverlay>();
	}
	PickupMessages->Show(GetWorld(), Text, Color, Seconds);
}

void AMainCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (PickupMessages.IsValid())
	{
		PickupMessages->Detach();
		PickupMessages.Reset();
	}
	Super::EndPlay(EndPlayReason);
}

void AMainCharacter::MakeInvincibleFor(float Seconds)
{
	bIsInvincible = true;
	if (IsLocallyControlled())
	{
		if (!PickupMessages.IsValid())
		{
			PickupMessages = MakeShared<FPickupMessageOverlay>();
		}
		PickupMessages->ShowCountdown(GetWorld(), TEXT("BULLETPROOF"), FLinearColor(0.45f, 0.85f, 1.f),
			GetWorld()->GetTimeSeconds() + Seconds);
	}
	GetWorld()->GetTimerManager().SetTimer(
		InvincibilityTimerHandle,
		this,
		&AMainCharacter::OnInvincibilityFinished,
		Seconds,
		false);
}

void AMainCharacter::OnInvincibilityFinished()
{
	bIsInvincible = false;
}

float AMainCharacter::Heal(const float AdditionalHealth)
{
	const float Before = Health;
	if (Health < MaxHealth && AdditionalHealth > 0)
	{
		ChangeHealth(Health + AdditionalHealth);
	}
	return Health - Before;
}

void AMainCharacter::TeleportToLocation(FVector Location)
{
	SetActorLocation(Location);
}


void AMainCharacter::ToggleView(const FInputActionValue& Value)
{
	bThirdPerson = !bThirdPerson;
	UpdateActiveCamera();
}

void AMainCharacter::UpdateActiveCamera()
{
	const bool bUseThird = bThirdPerson && !ScopeButtonDown;
	ThirdPersonCamera->SetActive(bUseThird);
	CameraComponent->SetActive(!bUseThird);

	// third person: the mouse orbits the camera around the character (all sides), the body turns to where it walks;
	// first person (and aiming): the body follows the view as before
	bUseControllerRotationYaw = !bUseThird;
	if (UCharacterMovementComponent* MoveComp = GetCharacterMovement())
	{
		MoveComp->bOrientRotationToMovement = bUseThird;
		MoveComp->RotationRate = FRotator(0.f, 540.f, 0.f);
	}
}

void AMainCharacter::FaceViewDirection()
{
	if (!Controller) return;
	SetActorRotation(FRotator(0.f, Controller->GetControlRotation().Yaw, 0.f));
}

UCameraComponent* AMainCharacter::GetViewCamera() const
{
	return ThirdPersonCamera && ThirdPersonCamera->IsActive() ? ThirdPersonCamera : CameraComponent;
}

void AMainCharacter::HideCameraModels() const
{
	// editor-only helpers attached to the cameras (camera model, frustum) - hidden in play as well
	for (UCameraComponent* Cam : {CameraComponent, ThirdPersonCamera})
	{
		if (!Cam) continue;
		TArray<USceneComponent*> CameraHelpers;
		Cam->GetChildrenComponents(true, CameraHelpers);
		for (USceneComponent* Helper : CameraHelpers)
		{
			if (UPrimitiveComponent* Prim = Cast<UPrimitiveComponent>(Helper))
			{
				Prim->SetHiddenInGame(true);
				Prim->SetVisibility(false);
			}
		}
	}
}
