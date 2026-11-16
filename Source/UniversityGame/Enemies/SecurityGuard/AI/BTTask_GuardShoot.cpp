#include "BTTask_GuardShoot.h"

#include "SecurityGuardAIController.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "UniversityGame/Enemies/SecurityGuard/SecurityGuard.h"

UBTTask_GuardShoot::UBTTask_GuardShoot()
{
	NodeName = TEXT("Guard Shoot Burst");
	bNotifyTick = true;
	bCreateNodeInstance = true;
}

EBTNodeResult::Type UBTTask_GuardShoot::ExecuteTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory)
{
	const AAIController* AI = OwnerComp.GetAIOwner();
	const ASecurityGuard* Guard = AI ? Cast<ASecurityGuard>(AI->GetPawn()) : nullptr;
	const UBlackboardComponent* BB = OwnerComp.GetBlackboardComponent();
	if (!Guard || !BB || !BB->GetValueAsObject(GuardKeys::TargetActor))
	{
		return EBTNodeResult::Failed;
	}
	const float Now = OwnerComp.GetWorld()->GetTimeSeconds();
	ShotsLeft = ShotsPerBurst;
	NextShot = Now + 0.15f;                      // a moment to raise the rifle / finish turning
	EndTime = 0.f;
	return EBTNodeResult::InProgress;
}

void UBTTask_GuardShoot::TickTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory, float DeltaSeconds)
{
	AAIController* AI = OwnerComp.GetAIOwner();
	ASecurityGuard* Guard = AI ? Cast<ASecurityGuard>(AI->GetPawn()) : nullptr;
	const UBlackboardComponent* BB = OwnerComp.GetBlackboardComponent();
	const AActor* Target = BB ? Cast<AActor>(BB->GetValueAsObject(GuardKeys::TargetActor)) : nullptr;
	const float Now = OwnerComp.GetWorld()->GetTimeSeconds();

	if (!Guard || Guard->IsDead() || !Target || !BB->GetValueAsBool(GuardKeys::CanSeeTarget))
	{
		FinishLatentTask(OwnerComp, EBTNodeResult::Failed);
		return;
	}
	if (EndTime > 0.f)
	{
		if (Now >= EndTime) FinishLatentTask(OwnerComp, EBTNodeResult::Succeeded);
		return;
	}
	AI->StopMovement();
	if (Now >= NextShot && !Guard->IsBusy())
	{
		// only shoot when he is roughly facing the player (turning is smooth, so wait for it)
		const FVector ToTarget = (Target->GetActorLocation() - Guard->GetActorLocation()).GetSafeNormal2D();
		if (FVector::DotProduct(ToTarget, Guard->GetActorForwardVector()) > 0.9f && Guard->ShootAt(Target))
		{
			ShotsLeft--;
			NextShot = Now + FMath::Max(ShotInterval, Guard->GetFireInterval());
			if (ShotsLeft <= 0)
			{
				EndTime = Now + PauseAfterBurst * FMath::FRandRange(0.8f, 1.3f);
			}
		}
	}
}

FString UBTTask_GuardShoot::GetStaticDescription() const
{
	return FString::Printf(TEXT("%d shots every %.2f s, then %.1f s pause"), ShotsPerBurst, ShotInterval, PauseAfterBurst);
}
