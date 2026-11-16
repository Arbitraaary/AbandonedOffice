// Fill out your copyright notice in the Description page of Project Settings.


#include "Enemy.h"

#include "EnemyHealthBarWidget.h"
#include "AI/SoldierAIController.h"
#include "Components/WidgetComponent.h"
#include "Components/CapsuleComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "SoldierHealthBarWidget.h"
#include "Kismet/KismetMathLibrary.h"
#include "UniversityGame/Weapons/BaseWeapon.h"

// Sets default values
AEnemy::AEnemy() :
HealthBarWidgetComponent{CreateDefaultSubobject<UWidgetComponent>(TEXT("HealthBarWidgetComponent"))}
{
 	// Set this character to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;
	SetCanBeDamaged(true);
	
	Health = MaxHealth;
	
	if (HealthBarWidgetComponent)
	{
		HealthBarWidgetComponent->SetupAttachment(RootComponent);
		HealthBarWidgetComponent->SetWidgetSpace(EWidgetSpace::Screen);
		HealthBarWidgetComponent->SetRelativeLocation(FVector(0.f, 0.f, 0.f));
		HealthBarWidgetComponent->SetPivot(FVector2D(0.5f, 1.f));          // bottom-centre of the bar = the point above the head
		HealthBarWidgetComponent->SetDrawAtDesiredSize(false);
		if (UEnemyHealthBarWidget* HealthBarWidget = Cast<UEnemyHealthBarWidget>(HealthBarWidgetComponent->GetWidget());
			HealthBarWidget != nullptr)
		{
			HealthBarWidget->UpdateHealthPercentage(Health / MaxHealth);
		}
	}
}

// Called when the game starts or when spawned
void AEnemy::BeginPlay()
{
	Super::BeginPlay();

	if (HealthBarWidgetComponent)
	{
		// the soldiers' widget blueprint is a big canvas with the bar somewhere inside it, so it could not be placed
		// exactly over the head - it is swapped for a C++ bar of the bar's own size (C++ bars, like the guard's, stay)
		const UClass* BarClass = HealthBarWidgetComponent->GetWidgetClass();
		if (!BarClass || !BarClass->HasAnyClassFlags(CLASS_Native))
		{
			HealthBarWidgetComponent->SetWidgetClass(USoldierHealthBarWidget::StaticClass());
			if (!Cast<USoldierHealthBarWidget>(HealthBarWidgetComponent->GetWidget()))
			{
				HealthBarWidgetComponent->SetWidget(CreateWidget<USoldierHealthBarWidget>(GetWorld(), USoldierHealthBarWidget::StaticClass()));
			}
			HealthBarWidgetComponent->SetDrawSize(FVector2D(USoldierHealthBarWidget::Width, USoldierHealthBarWidget::Height));
		}
		HealthBarWidgetComponent->SetWidgetSpace(EWidgetSpace::Screen);
		HealthBarWidgetComponent->SetPivot(FVector2D(0.5f, 1.f));
		HealthBarWidgetComponent->SetDrawAtDesiredSize(false);
		if (UEnemyHealthBarWidget* Bar = Cast<UEnemyHealthBarWidget>(HealthBarWidgetComponent->GetWidget()))
		{
			Bar->UpdateHealthPercentage(Health / MaxHealth);
		}
		UpdateHealthBar();
	}
	
	FActorSpawnParameters SpawnParams;
	SpawnParams.Owner = this;
	SpawnParams.Instigator = GetInstigator();
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	
	Weapon = GetWorld()->SpawnActor<ABaseWeapon>(
		WeaponClass,
		FVector(0.f, 0.f, 0.f),
		FRotator(0.f, 0.f, 0.f),
		SpawnParams);
	if(Weapon)
	{
		Weapon->SetActorEnableCollision(false);
		Weapon->SetInfiniteAmmo(true);
		Weapon->AttachToComponent(GetMesh(), FAttachmentTransformRules(EAttachmentRule::SnapToTarget, true), WeaponSocketName);
	}
}

void AEnemy::Fire()
{
	if (WeaponClass == nullptr) return;
	if (!CanShoot || IsDying) return;

	const FVector MuzzleDirection = Weapon->GetWeaponDirection();
	
	const FVector LaunchDirection = UKismetMathLibrary::Normal(MuzzleDirection);
	
	if (Weapon->ReadyToFire())
		Weapon->Fire(LaunchDirection.Rotation(), LaunchDirection);

	if (Weapon->IsMagEmpty())
		Reload();
	
}

void AEnemy::Reload()
{
	if (Weapon->CanReload())
	{
		
		CanShoot = false;
		
		if(const auto SoldierController = Cast<ASoldierAIController>(GetController()); SoldierController != nullptr)
		{
			SoldierController->SetIsReloading(true);
		}
		OnReload();

		Weapon->Reload();
		
	}
}

void AEnemy::OnReloadFinal()
{
	CanShoot = true;
	if(const auto SoldierController = Cast<ASoldierAIController>(GetController()); SoldierController != nullptr)
	{
		SoldierController->SetIsReloading(false);
	}
}

void AEnemy::OnDeathFinal()
{
	//DropWeapon();
	Destroy();
}

void AEnemy::OnBeingShotFinal()
{
	CanPlayShotAnim = true;
	if(const auto SoldierController = Cast<ASoldierAIController>(GetController()); SoldierController != nullptr)
	{
		SoldierController->SetIsHit(false);
	}
}

void AEnemy::DropWeapon()
{
	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
	const FTransform WeaponTransform = Weapon->GetActorTransform();

	if (ABaseWeapon* DroppedWeapon = Cast<ABaseWeapon>(GetWorld()->SpawnActor(WeaponClass, &WeaponTransform, SpawnParams));
		DroppedWeapon != nullptr
	)
	{
		// the dropped weapon must be "Pickable" (GameTraceChannel2) - the player's E-pickup only looks for that type
		DroppedWeapon->SkeletalMeshComponent->SetCollisionObjectType(ECC_GameTraceChannel2);
		DroppedWeapon->SkeletalMeshComponent->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		DroppedWeapon->SkeletalMeshComponent->SetSimulatePhysics(true);
		DroppedWeapon->CopyFrom(Weapon);
	
		Weapon->Destroy();
		Weapon = nullptr;
	}
}

// Called every frame
void AEnemy::UpdateHealthBar()
{
	if (!HealthBarWidgetComponent) return;
	if (IsDying)
	{
		HealthBarWidgetComponent->SetVisibility(false);
		return;
	}

	// right above the head, wherever the animation takes it (dodge, hit reaction)
	const USkeletalMeshComponent* Body = GetMesh();
	const float Scale = GetActorScale3D().Z;
	FVector Top = Body && Body->DoesSocketExist(TEXT("head"))
		              ? Body->GetSocketLocation(TEXT("head")) + FVector(0.f, 0.f, BarAboveHead * Scale)
		              : GetActorLocation() + FVector(0.f, 0.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 8.f);
	HealthBarWidgetComponent->SetWorldLocation(Top);

	// a screen-space widget is drawn over everything, so hide it ourselves when a wall/floor covers the enemy
	bool bVisible = true;
	if (const APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		FCollisionObjectQueryParams Solid;
		Solid.AddObjectTypesToQuery(ECC_WorldStatic);
		Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
		FCollisionQueryParams Params(SCENE_QUERY_STAT(EnemyBarVisibility), false, this);
		if (Weapon) Params.AddIgnoredActor(Weapon);
		if (APawn* PlayerPawn = UGameplayStatics::GetPlayerPawn(this, 0)) Params.AddIgnoredActor(PlayerPawn);
		const FVector Eye = Cam->GetCameraLocation();
		const FVector Head = Top - FVector(0.f, 0.f, BarAboveHead * Scale * 0.5f);
		bVisible = !GetWorld()->LineTraceTestByObjectType(Eye, Head, Solid, Params);
	}
	HealthBarWidgetComponent->SetVisibility(bVisible);
}

void AEnemy::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	UpdateHealthBar();
	
	if (bAutoFire)
	{
		Fire();
	}
}

// Called to bind functionality to input
void AEnemy::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

}

float AEnemy::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator,
	AActor* DamageCauser)
{
	if (IsImmortal || IsDying) return 0;
	// enemies are hurt only by the player (or by an obstacle, reported as their own controller) -
	// a stray bullet of another enemy (soldier or guard) does nothing
	if (EventInstigator != nullptr && !EventInstigator->IsPlayerController() && EventInstigator->GetPawn() != this) return 0;
	
	if (Health > 0)
	{
		Health -= DamageAmount;
		if (UEnemyHealthBarWidget* HealthBarWidget = Cast<UEnemyHealthBarWidget>(HealthBarWidgetComponent->GetWidget());
			HealthBarWidget != nullptr)
		{
			HealthBarWidget->UpdateHealthPercentage(Health / MaxHealth);
		}
		UE_LOG(LogTemp, Warning, TEXT("%s has %f amount of health left. Instigator controller: %s"), *GetName(), Health, *(EventInstigator->GetName()));
		if (CanPlayShotAnim)
		{
			CanPlayShotAnim = false;
			if(const auto SoldierController = Cast<ASoldierAIController>(GetController()); SoldierController != nullptr)
			{
				SoldierController->SetIsHit(true);
			}
			OnBeingShot();
		}
	}

	if (Health <= 0 && !IsDying)
	{
		IsDying = true;
		if(const auto SoldierController = Cast<ASoldierAIController>(GetController()); SoldierController != nullptr)
		{
			SoldierController->SetIsDying(true);
		}
		DropWeapon();
		OnDeath();
	}

	return DamageAmount;
	
}

UBehaviorTree* AEnemy::GetBehaviorTree() const
{
	return BehaviorTree;
}

TArray<ATargetPoint*>& AEnemy::GetTargetPoints()
{
	return TargetPoints;
}
