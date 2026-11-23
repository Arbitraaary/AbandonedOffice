#include "SecurityGuard.h"

#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "GuardHealthBarWidget.h"
#include "NavigationSystem.h"
#include "AI/SecurityGuardAIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "BrainComponent.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/WidgetComponent.h"
#include "Engine/TargetPoint.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/Engine.h"
#include "UniversityGame/Environment/Hazards/SmokeZone.h"
#include "UObject/ConstructorHelpers.h"
#include "UniversityGame/Weapons/BaseWeapon.h"
#include "UniversityGame/Weapons/Bullet.h"

namespace GuardAnims
{
	const FName GuardSlot(TEXT("DefaultSlot"));

	UAnimSequenceBase* FindAnim(const TCHAR* Path)
	{
		ConstructorHelpers::FObjectFinder<UAnimSequenceBase> Finder(Path);
		return Finder.Succeeded() ? Finder.Object : nullptr;
	}
}
using namespace GuardAnims;

ASecurityGuard::ASecurityGuard()
{
	MaxHealth = 150.f;
	Health = MaxHealth;

	// the guard shoots only when his behavior tree tells him to, rifle in the right hand
	bAutoFire = false;
	// the cap is a bit higher than a bare head
	BarAboveHead = 29.f;
	WeaponSocketName = TEXT("hand_r_val_socket");

	AIControllerClass = ASecurityGuardAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;

	// smooth turning: the body follows the controller's desired rotation at TurnRate instead of snapping to it
	bUseControllerRotationYaw = false;
	if (UCharacterMovementComponent* Move = GetCharacterMovement())
	{
		Move->bUseControllerDesiredRotation = true;
		Move->bOrientRotationToMovement = false;
		Move->RotationRate = FRotator(0.f, TurnRate, 0.f);
		Move->MaxWalkSpeed = WalkSpeed;
		Move->BrakingDecelerationWalking = 900.f;
		Move->MaxAcceleration = 900.f;
		Move->AirControl = 0.1f;
	}

	// thin solid blue bar above the head (soldiers have their own UMG bar); "DODGE" text appears above the bar
	if (HealthBarWidgetComponent)
	{
		HealthBarWidgetComponent->SetWidgetClass(UGuardHealthBarWidget::StaticClass());
		HealthBarWidgetComponent->SetDrawSize(FVector2D(UGuardHealthBarWidget::Width, UGuardHealthBarWidget::TotalHeight));
		HealthBarWidgetComponent->SetRelativeLocation(FVector(0.f, 0.f, 112.f));
		HealthBarWidgetComponent->SetPivot(FVector2D(0.5f, 1.f));
	}

	HitReactions = {FindAnim(TEXT("/Game/AnimStarterPack/Hit_React_1")), FindAnim(TEXT("/Game/AnimStarterPack/Hit_React_2")),
	                FindAnim(TEXT("/Game/AnimStarterPack/Hit_React_3")), FindAnim(TEXT("/Game/AnimStarterPack/Hit_React_4"))};
	DodgeLeft = FindAnim(TEXT("/Game/AnimStarterPack/Jog_Lt_Rifle"));
	DodgeRight = FindAnim(TEXT("/Game/AnimStarterPack/Jog_Rt_Rifle"));
	Deaths = {FindAnim(TEXT("/Game/AnimStarterPack/Death_1")), FindAnim(TEXT("/Game/AnimStarterPack/Death_2")),
	          FindAnim(TEXT("/Game/AnimStarterPack/Death_3"))};
	Deaths.Remove(nullptr);
	LookAroundIdles = {FindAnim(TEXT("/Game/AnimStarterPack/Idle_Rifle_Hip_Break1")),
	                   FindAnim(TEXT("/Game/AnimStarterPack/Idle_Rifle_Hip_Break2"))};
	ReloadAnim = FindAnim(TEXT("/Game/AnimStarterPack/Reload_Rifle_Hip"));
	HitReactions.Remove(nullptr);
	LookAroundIdles.Remove(nullptr);
}

void ASecurityGuard::BeginPlay()
{
	Super::BeginPlay();
	Health = MaxHealth;
	Home = GetActorLocation();
	if (UCharacterMovementComponent* Move = GetCharacterMovement())
	{
		Move->RotationRate = FRotator(0.f, TurnRate, 0.f);
	}
	SetRunning(false);
	if (HealthBarWidgetComponent)
	{
		HealthBarWidgetComponent->InitWidget();
		if (UGuardHealthBarWidget* Bar = GetBar())
		{
			Bar->UpdateHealthPercentage(1.f);
		}
	}
}

void ASecurityGuard::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	if (!IsDying)
	{
		WatchIncomingBullets();
		UpdateWeaponPose(DeltaTime);

		// smoke: blind and slow while inside
		const bool bNowInSmoke = ASmokeZone::IsActorInSmoke(this);
		const float Now = GetWorld()->GetTimeSeconds();
		if (bNowInSmoke != bInSmoke)
		{
			bInSmoke = bNowInSmoke;
			SetRunning(bRunning);
			NextSmokeMessage = 0.f;
		}
		if (bInSmoke && Now >= NextSmokeMessage)
		{
			ShowStatus(TEXT("BLINDED"), FLinearColor(0.8f, 0.8f, 0.8f), 1.3f);
			NextSmokeMessage = Now + 1.2f;
		}
	}
	else if (bDeathHandled && GetWorld()->GetTimeSeconds() < DeathTime + 3.f)
	{
		KeepBodyOutOfWalls();
	}
}

void ASecurityGuard::KeepBodyOutOfWalls()
{
	// the death animation knows nothing about the level: while he falls, push the body back out of walls / furniture
	// and lift it onto stairs, so he never ends up half inside the geometry
	USkeletalMeshComponent* Body = GetMesh();
	if (!Body) return;
	UWorld* World = GetWorld();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GuardBody), false, this);
	if (Weapon) Params.AddIgnoredActor(Weapon);
	if (!bBodyPushIgnoredReady)
	{
		// moving things like the sliding glass door are not walls: the body must not be lifted onto them
		TArray<AActor*> Found;
		UGameplayStatics::GetAllActorsWithTag(this, FName("NoBodyPush"), Found);
		BodyPushIgnored.Append(Found);
		bBodyPushIgnoredReady = true;
	}
	for (AActor* A : BodyPushIgnored)
	{
		if (A) Params.AddIgnoredActor(A);
	}
	FCollisionObjectQueryParams Solid;
	Solid.AddObjectTypesToQuery(ECC_WorldStatic);
	Solid.AddObjectTypesToQuery(ECC_WorldDynamic);

	// 1) horizontal: from where he stood, is the way to the head / pelvis blocked by a wall?
	FVector Shift = FVector::ZeroVector;
	const FVector Start = DeathOrigin + GetActorLocation() - DeathActorLocation;   // follows earlier corrections
	for (const TCHAR* Bone : {TEXT("head"), TEXT("spine_03"), TEXT("pelvis")})
	{
		const FVector P = Body->GetSocketLocation(Bone);
		const FVector To(P.X, P.Y, Start.Z);
		FHitResult Hit;
		if (FVector::Dist2D(Start, To) > 5.f &&
			World->SweepSingleByObjectType(Hit, Start, To, FQuat::Identity, Solid, FCollisionShape::MakeSphere(14.f), Params))
		{
			const FVector Over = (To - Hit.Location) * FVector(1.f, 1.f, 0.f);    // how far it went into the wall
			if (Over.SizeSquared() > Shift.SizeSquared()) Shift = Over;
		}
	}

	// 2) vertical: a bone that ended up inside a step / the floor is lifted onto its surface
	//    (only bones really inside something - a body under a desk is not lifted onto the desk)
	float Lift = 0.f;
	for (const TCHAR* Bone : {TEXT("head"), TEXT("spine_03"), TEXT("pelvis"), TEXT("calf_l"), TEXT("calf_r")})
	{
		const FVector P = Body->GetSocketLocation(Bone) - Shift;
		if (!World->OverlapAnyTestByObjectType(P, FQuat::Identity, Solid, FCollisionShape::MakeSphere(6.f), Params))
		{
			continue;
		}
		FHitResult Hit;
		if (World->LineTraceSingleByObjectType(Hit, P + FVector(0.f, 0.f, 80.f), P, Solid, Params))
		{
			Lift = FMath::Max(Lift, Hit.ImpactPoint.Z + 9.f - P.Z);
		}
	}
	Lift = FMath::Clamp(Lift, 0.f, 70.f);

	if (!Shift.IsNearlyZero(0.5f) || Lift > 0.5f)
	{
		AddActorWorldOffset(-Shift + FVector(0.f, 0.f, Lift));
	}
}

// ==================================================================== movement
void ASecurityGuard::SetRunning(const bool bRun)
{
	bRunning = bRun;
	if (UCharacterMovementComponent* Move = GetCharacterMovement())
	{
		// in smoke he cannot run - he feels his way out slowly
		Move->MaxWalkSpeed = bStunned ? 0.f : bInSmoke ? WalkSpeed * 0.6f : (bRun ? RunSpeed : WalkSpeed);
	}
}

FVector ASecurityGuard::PickPatrolLocation()
{
	TArray<ATargetPoint*>& Points = GetTargetPoints();
	Points.Remove(nullptr);
	if (Points.Num() > 0)
	{
		// patrol points in order; after looking around he may also turn back the way he came
		if (Points.Num() > 2 && FMath::FRand() < 0.25f)
		{
			NextPatrolIndex = (NextPatrolIndex + Points.Num() - 2) % Points.Num();
		}
		const FVector P = Points[NextPatrolIndex % Points.Num()]->GetActorLocation();
		NextPatrolIndex = (NextPatrolIndex + 1) % Points.Num();
		return P;
	}

	// no points: a random reachable spot around home on the same floor (not on the stairs),
	// at least a few metres away from where he stands now
	if (const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
	{
		for (int32 Try = 0; Try < 8; ++Try)
		{
			FNavLocation Out;
			if (Nav->GetRandomReachablePointInRadius(Home, PatrolRadius, Out) &&
				FVector::Dist2D(Out.Location, GetActorLocation()) > 300.f && FMath::Abs(Out.Location.Z - Home.Z) < 40.f)
			{
				return Out.Location;
			}
		}
	}
	return Home;
}

// ==================================================================== shooting
float ASecurityGuard::GetFireInterval() const
{
	return Weapon ? FMath::Max(Weapon->GetFireRate(), 0.08f) : 0.2f;
}

bool ASecurityGuard::IsBusy() const
{
	return IsDying || GetWorld()->GetTimeSeconds() < BusyUntil;
}

bool ASecurityGuard::ShootAt(const AActor* Target)
{
	if (!Weapon || !Target || IsDying || bReloading)
	{
		return false;
	}
	if (Weapon->IsMagEmpty())
	{
		StartReload();
		return false;
	}
	if (!Weapon->ReadyToFire())
	{
		return false;
	}

	// aim at the chest, with a little spread
	const FVector Muzzle = Weapon->GetMuzzleLocation();
	const FVector Aim = Target->GetActorLocation() + FVector(0.f, 0.f, 20.f);
	const FVector Dir = FMath::VRandCone((Aim - Muzzle).GetSafeNormal(), FMath::DegreesToRadians(AimSpreadDeg));
	Weapon->Fire(Dir.Rotation(), Dir);
	if (Weapon->IsMagEmpty())
	{
		StartReload();
	}
	return true;
}

void ASecurityGuard::StartReload()
{
	if (bReloading || IsDying) return;
	bReloading = true;
	const UAnimMontage* M = PlayAnim(ReloadAnim, 1.2f);
	const float Time = M ? M->GetPlayLength() / 1.2f : 1.5f;
	GetWorldTimerManager().SetTimer(ReloadTimer, this, &ASecurityGuard::FinishReload, FMath::Max(Time, 0.8f), false);
}

void ASecurityGuard::FinishReload()
{
	bReloading = false;
	if (Weapon) Weapon->Reload();
}

// ==================================================================== dodge
float ASecurityGuard::DodgeChanceForDistance(const float Distance) const
{
	// proportional to the distance the shot came from
	return FMath::Clamp(Distance / DodgeFullDistance, 0.f, 1.f) * (MaxDodgeChance - MinDodgeChance) + MinDodgeChance;
}

void ASecurityGuard::WatchIncomingBullets()
{
	const UWorld* World = GetWorld();
	const float Now = World->GetTimeSeconds();
	const FVector Me = GetActorLocation();
	const float Radius = GetCapsuleComponent()->GetScaledCapsuleRadius();
	const float HalfHeight = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();

	for (TActorIterator<ABullet> It(GetWorld()); It; ++It)
	{
		ABullet* Bullet = *It;
		const APawn* Shooter = Bullet->GetInstigator();
		if (!Shooter || !Shooter->IsPlayerControlled() || JudgedBullets.Contains(Bullet))
		{
			continue;
		}

		// bullet velocity: from its projectile movement, or measured from how far it moved since the last frame
		FVector V = FVector::ZeroVector;
		if (const UProjectileMovementComponent* PM = Bullet->FindComponentByClass<UProjectileMovementComponent>())
		{
			V = PM->Velocity;
		}
		const FVector Pos = Bullet->GetActorLocation();
		if (const FVector* Prev = LastBulletPos.Find(Bullet); V.SizeSquared() < 1.f && Prev && World->GetDeltaSeconds() > 0.f)
		{
			V = (Pos - *Prev) / World->GetDeltaSeconds();
		}
		LastBulletPos.Add(Bullet, Pos);
		const float BulletSpeed = V.Size();
		if (BulletSpeed < 1.f) continue;

		// where will it pass him? closest approach in the horizontal plane, and at what height
		const FVector Dir = V / BulletSpeed;
		const FVector ToMe = Me - Pos;
		const FVector Dir2D = FVector(Dir.X, Dir.Y, 0.f);
		const float Speed2D = Dir2D.Size();
		if (Speed2D < 0.05f) continue;                                     // flying straight up / down
		const float Along2D = FVector::DotProduct(FVector(ToMe.X, ToMe.Y, 0.f), Dir2D / Speed2D);
		if (Along2D <= 0.f) continue;                                     // flying away from him
		const float Miss2D = (FVector(ToMe.X, ToMe.Y, 0.f) - Dir2D / Speed2D * Along2D).Size();
		const float TimeToReach = Along2D / (BulletSpeed * Speed2D);
		const float ZThere = Pos.Z + V.Z * TimeToReach;
		if (Miss2D > Radius + 50.f || FMath::Abs(ZThere - Me.Z) > HalfHeight + 30.f) continue;   // will miss him anyway
		if (TimeToReach > 1.f) continue;                                   // still far: judge it a bit later

		// one decision per bullet: the further the shooter, the more time to react -> the higher the chance
		JudgedBullets.Add(Bullet);
		const float Distance = FVector::Dist(Shooter->GetActorLocation(), Me);
		const float Chance = DodgeChanceForDistance(Distance);
		const float Roll = FMath::FRand();
		const bool bCanDodge = Now >= NextDodgeTime && !GetCharacterMovement()->IsFalling() && !IsDying;
		const bool bWants = bCanDodge && Roll < Chance;
		const bool bDodge = bWants && Dodge(V, Chance);
		AlertController(const_cast<APawn*>(Shooter));
		if (bShowDodgeDebug && GEngine)
		{
			const TCHAR* Result = bDodge ? TEXT("DODGE") : bWants ? TEXT("no dodge (no room to jump)")
			                    : bCanDodge ? TEXT("no dodge") : TEXT("no dodge (still recovering)");
			GEngine->AddOnScreenDebugMessage(-1, 3.f, bDodge ? FColor::Cyan : FColor::Silver,
				FString::Printf(TEXT("%s: shot from %.1f m -> dodge chance %.0f%%, roll %.0f -> %s"), *GetName(),
				                Distance / 100.f, Chance * 100.f, Roll * 100.f, Result));
		}
	}

	// forget bullets that no longer exist
	for (auto It = JudgedBullets.CreateIterator(); It; ++It)
	{
		if (!It->IsValid()) It.RemoveCurrent();
	}
	for (auto It = LastBulletPos.CreateIterator(); It; ++It)
	{
		if (!It->Key.IsValid()) It.RemoveCurrent();
	}
}

float ASecurityGuard::FreeSpace(const FVector& Dir, const float MaxDistance) const
{
	// sweep a slightly fatter capsule (shoulders and rifle stick out of the collision capsule) sideways
	const UCapsuleComponent* Cap = GetCapsuleComponent();
	const FCollisionShape Shape = FCollisionShape::MakeCapsule(Cap->GetScaledCapsuleRadius() + 18.f,
	                                                           Cap->GetScaledCapsuleHalfHeight() - 10.f);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GuardDodge), false, this);
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	const FVector From = GetActorLocation() + FVector(0.f, 0.f, 8.f);
	FHitResult Hit;
	if (GetWorld()->SweepSingleByObjectType(Hit, From, From + Dir * MaxDistance, FQuat::Identity, Objects, Shape, Params))
	{
		return Hit.bStartPenetrating ? 0.f : Hit.Distance;
	}
	return MaxDistance;
}

bool ASecurityGuard::Dodge(const FVector& BulletVelocity, const float Chance)
{
	// jump sideways, perpendicular to the bullet, to the side with more free space - never into a wall
	const FVector Side = FVector::CrossProduct(BulletVelocity.GetSafeNormal2D(), FVector::UpVector).GetSafeNormal();
	constexpr float WantedDistance = 260.f;           // how far a full dodge jump carries him
	const float FreeA = FreeSpace(Side, WantedDistance + 40.f);
	const float FreeB = FreeSpace(-Side, WantedDistance + 40.f);
	float Room = FreeA;
	FVector JumpDir = Side;
	if (FreeB > FreeA || (FreeB == FreeA && FMath::RandBool()))
	{
		Room = FreeB;
		JumpDir = -Side;
	}
	if (Room < 110.f)
	{
		return false;                                 // squeezed between obstacles - nowhere to jump
	}
	// shorter jump when there is less room (he stops before the obstacle, not in it)
	const float Scale = FMath::Clamp((Room - 40.f) / WantedDistance, 0.35f, 1.f);
	LaunchCharacter(JumpDir * DodgeSpeed * Scale + FVector(0.f, 0.f, 230.f), true, true);
	const bool bRight = FVector::DotProduct(JumpDir, GetActorRightVector()) > 0.f;
	if (UAnimMontage* M = PlayAnim(bRight ? DodgeRight : DodgeLeft, 1.6f, 0.05f, 0.15f))
	{
		// only the first steps of the side jog - stop it when he lands
		TWeakObjectPtr<ASecurityGuard> Self(this);
		GetWorldTimerManager().SetTimer(DodgeAnimTimer, [Self, M]()
		{
			if (Self.IsValid() && Self->GetMesh() && Self->GetMesh()->GetAnimInstance())
			{
				Self->GetMesh()->GetAnimInstance()->Montage_Stop(0.2f, M);
			}
		}, 0.55f, false);
	}

	const float Now = GetWorld()->GetTimeSeconds();
	NextDodgeTime = Now + DodgeCooldown;
	BusyUntil = Now + 0.6f;
	if (UGuardHealthBarWidget* Bar = GetBar())
	{
		Bar->ShowDodge(Chance);
	}
	UE_LOG(LogTemp, Log, TEXT("%s dodged (chance %.0f%%)"), *GetName(), Chance * 100.f);
	return true;
}

// ==================================================================== being hit / dying
float ASecurityGuard::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator,
                                 AActor* DamageCauser)
{
	if (IsDying) return 0.f;
	// only the player (and the obstacles) can hurt him - soldiers' stray bullets must not kill the guard
	const bool bFromPlayer = EventInstigator && EventInstigator->IsPlayerController();
	if (!bFromPlayer && !bHazardDamage)
	{
		return 0.f;
	}
	if (DamageCauser)
	{
		LastHitDirection = (GetActorLocation() - DamageCauser->GetActorLocation()).GetSafeNormal2D();
	}
	const float Done = Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
	CanPlayShotAnim = true;                         // the soldiers' blueprint resets this, the guard does it himself

	if (IsDying)
	{
		Die();
		return Done;
	}

	// visible reaction: flinch animation, a small push away from the shot, the bar flashes, he turns to the shooter
	if (HitReactions.Num() > 0)
	{
		PlayAnim(HitReactions[FMath::RandRange(0, HitReactions.Num() - 1)], 1.15f, 0.05f, 0.2f);
	}
	const FVector From = DamageCauser ? DamageCauser->GetActorLocation() : GetActorLocation() - GetActorForwardVector();
	const FVector Push = (GetActorLocation() - From).GetSafeNormal2D();
	LaunchCharacter(Push * 180.f, true, false);
	BusyUntil = GetWorld()->GetTimeSeconds() + 0.35f;
	if (UGuardHealthBarWidget* Bar = GetBar())
	{
		Bar->Flash();
	}
	if (bFromPlayer)
	{
		AlertController(EventInstigator->GetPawn());
	}
	return Done;
}

void ASecurityGuard::Die()
{
	if (bDeathHandled) return;
	bDeathHandled = true;

	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		if (AI->GetBrainComponent()) AI->GetBrainComponent()->StopLogic(TEXT("dead"));
		AI->StopMovement();
		AI->ClearFocus(EAIFocusPriority::Gameplay);
	}
	GetCharacterMovement()->DisableMovement();
	DeathTime = GetWorld()->GetTimeSeconds();
	DeathActorLocation = GetActorLocation();
	DeathOrigin = GetActorLocation() + FVector(0.f, 0.f, 10.f);
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetWorldTimerManager().ClearTimer(ReloadTimer);
	GetWorldTimerManager().ClearTimer(ShakeTimer);
	GetWorldTimerManager().ClearTimer(StunTimer);
	if (HealthBarWidgetComponent) HealthBarWidgetComponent->SetVisibility(false);

	// fall with one of the death animations and stay lying in its last pose (no ragdoll - it twists the body)
	if (Deaths.Num() > 0)
	{
		if (UAnimMontage* M = PlayAnim(Deaths[FMath::RandRange(0, Deaths.Num() - 1)], 1.f, 0.1f, 0.f))
		{
			TWeakObjectPtr<ASecurityGuard> Self(this);
			GetWorldTimerManager().SetTimer(DeathPoseTimer, [Self, M]()
			{
				if (Self.IsValid() && Self->GetMesh() && Self->GetMesh()->GetAnimInstance())
				{
					Self->GetMesh()->GetAnimInstance()->Montage_Pause(M);
				}
			}, FMath::Max(M->GetPlayLength() - 0.1f, 0.1f), false);
		}
	}
	SetLifeSpan(8.f);
}

// ==================================================================== obstacles
void ASecurityGuard::Electrocute(const float Damage, const float StunSeconds, AActor* Source)
{
	if (IsDying) return;
	// the cables hurt but never kill him (they are an obstacle, not a weapon)
	const float Hurt = FMath::Min(Damage, Health - 10.f);
	if (Hurt > 0.f)
	{
		bHazardDamage = true;
		TakeDamage(Hurt, FDamageEvent(), GetController(), Source);
		bHazardDamage = false;
	}
	if (IsDying) return;

	// the jolt throws him out of the cables, so he does not stay inside and get shocked again and again
	FVector Away = GetActorLocation() - (Source ? Source->GetActorLocation() : GetActorLocation() - GetActorForwardVector());
	Away.Z = 0.f;
	Away = Away.IsNearlyZero() ? -GetActorForwardVector() : Away.GetSafeNormal();
	LaunchCharacter(Away * 480.f + FVector(0.f, 0.f, 260.f), true, true);

	ShowStatus(TEXT("SHOCKED!"), FLinearColor(1.f, 0.85f, 0.15f), StunSeconds);
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		AI->StopMovement();
	}
	bStunned = true;                                  // stands still (speed 0) until the stun is over
	SetRunning(bRunning);
	const float Now = GetWorld()->GetTimeSeconds();
	BusyUntil = Now + StunSeconds;
	ShakeUntil = Now + StunSeconds;

	// he shakes: short hit reactions one after another while the current goes through him
	TWeakObjectPtr<ASecurityGuard> Self(this);
	GetWorldTimerManager().SetTimer(ShakeTimer, [Self]()
	{
		if (!Self.IsValid() || Self->IsDying || Self->GetWorld()->GetTimeSeconds() > Self->ShakeUntil)
		{
			if (Self.IsValid()) Self->GetWorldTimerManager().ClearTimer(Self->ShakeTimer);
			return;
		}
		if (Self->HitReactions.Num() > 0)
		{
			Self->PlayAnim(Self->HitReactions[FMath::RandRange(0, Self->HitReactions.Num() - 1)], 2.2f, 0.03f, 0.08f);
		}
	}, 0.22f, true, 0.f);
	GetWorldTimerManager().SetTimer(StunTimer, [Self]()
	{
		if (Self.IsValid() && !Self->IsDying)
		{
			Self->bStunned = false;
			Self->SetRunning(Self->bRunning);
		}
	}, StunSeconds, false);
}

void ASecurityGuard::ShowStatus(const FString& Text, const FLinearColor& Color, const float Seconds) const
{
	if (UGuardHealthBarWidget* Bar = GetBar())
	{
		Bar->ShowStatus(Text, Color, Seconds);
	}
}

// ==================================================================== helpers
UAnimMontage* ASecurityGuard::PlayAnim(UAnimSequenceBase* Anim, const float Rate, const float BlendIn, const float BlendOut)
{
	UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	if (!Anim || !AnimInstance) return nullptr;
	return AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, GuardSlot, BlendIn, BlendOut, Rate);
}

float ASecurityGuard::PlayLookAroundIdle()
{
	// rifle lowered: no rifle-in-both-hands idle (it would override the relaxed pose through the slot) -
	// he just stands relaxed for a moment while the task turns him to look around
	if (WeaponRaiseAlpha < 0.5f) return 2.f;
	if (LookAroundIdles.Num() == 0) return 0.f;
	const UAnimMontage* M = PlayAnim(LookAroundIdles[FMath::RandRange(0, LookAroundIdles.Num() - 1)], 1.f, 0.25f, 0.3f);
	return M ? M->GetPlayLength() : 0.f;
}

UGuardHealthBarWidget* ASecurityGuard::GetBar() const
{
	return HealthBarWidgetComponent ? Cast<UGuardHealthBarWidget>(HealthBarWidgetComponent->GetWidget()) : nullptr;
}

void ASecurityGuard::AlertController(AActor* Threat) const
{
	if (ASecurityGuardAIController* AI = Cast<ASecurityGuardAIController>(GetController()))
	{
		AI->ReportThreat(Threat);
	}
}

// ==================================================================== weapon pose
void ASecurityGuard::UpdateWeaponPose(const float DeltaTime)
{
	// raise the rifle while the player is seen and within shooting range, lower it otherwise
	const AAIController* AI = Cast<AAIController>(GetController());
	const UBlackboardComponent* BB = AI ? AI->GetBlackboardComponent() : nullptr;
	const AActor* Target = BB ? Cast<AActor>(BB->GetValueAsObject(GuardKeys::TargetActor)) : nullptr;
	const bool bWantRaised = Target && !bStunned &&
		BB->GetValueAsBool(GuardKeys::CanSeeTarget) && BB->GetValueAsBool(GuardKeys::InAttackRange);

	bWantedRaised = bWantRaised;

	const float Step = DeltaTime / FMath::Max(bWantRaised ? RaiseTime : LowerTime, 0.05f);
	WeaponRaiseAlpha = FMath::Clamp(WeaponRaiseAlpha + (bWantRaised ? Step : -Step), 0.f, 1.f);
	bWeaponRaised = bWantRaised || WeaponRaiseAlpha > 0.f;

	// raised: the rifle follows the player up and down; the smooth-step makes the raise start and stop softly
	float AimPitch = 0.f;
	if (Target)
	{
		const FVector Eye = GetActorLocation() + FVector(0.f, 0.f, BaseEyeHeight * GetActorScale3D().Z);
		const FVector ToTarget = Target->GetActorLocation() - Eye;
		AimPitch = FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan2(ToTarget.Z, ToTarget.Size2D())), -45.f, 45.f);
	}
	const float Blend = FMath::SmoothStep(0.f, 1.f, WeaponRaiseAlpha);
	WeaponLoweredWeight = 1.f - Blend;                 // upper body: lowered pose -> combat pose
	WeaponAimPitch = AimPitch * Blend;                 // aims only once the rifle is up

	// debug line (off by default, Guard|Weapon -> Show Weapon Debug)
	if (bShowWeaponDebug && GEngine)
	{
		const UAnimInstance* Anim = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
		const UAnimMontage* Montage = Anim ? Anim->GetCurrentActiveMontage() : nullptr;
		GEngine->AddOnScreenDebugMessage(static_cast<uint64>(GetUniqueID()), 0.f, FColor::Yellow,
			FString::Printf(TEXT("%s  Sees:%d InRange:%d Target:%d  Lowered:%.2f  Montage:%s"), *GetName(),
			                BB ? BB->GetValueAsBool(GuardKeys::CanSeeTarget) : -1,
			                BB ? BB->GetValueAsBool(GuardKeys::InAttackRange) : -1, Target != nullptr,
			                WeaponLoweredWeight, Montage ? *Montage->GetName() : TEXT("-")));
	}
}
