#include "BTTask_GuardLookAround.h"

#include "SecurityGuardAIController.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "UniversityGame/Enemies/SecurityGuard/SecurityGuard.h"

UBTTask_GuardLookAround::UBTTask_GuardLookAround()
{
	NodeName = TEXT("Guard Look Around");
	bNotifyTick = true;
	bCreateNodeInstance = true;
}

EBTNodeResult::Type UBTTask_GuardLookAround::ExecuteTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory)
{
	AAIController* AI = OwnerComp.GetAIOwner();
	ASecurityGuard* Guard = AI ? Cast<ASecurityGuard>(AI->GetPawn()) : nullptr;
	if (!Guard)
	{
		return EBTNodeResult::Failed;
	}
	const UBlackboardComponent* BB = OwnerComp.GetBlackboardComponent();
	if (BB && BB->GetValueAsBool(GuardKeys::CanSeeTarget))
	{
		return EBTNodeResult::Succeeded;          // the player is right there - no time to look around
	}
	AI->StopMovement();
	Origin = Guard->GetActorLocation();
	BaseYaw = Guard->GetActorRotation().Yaw;
	Phase = 0;
	// phase 0: stand and play the look-around idle (head and shoulders turn), then turn left / right / back
	PhaseEnd = OwnerComp.GetWorld()->GetTimeSeconds() + FMath::Clamp(Guard->PlayLookAroundIdle() * 0.6f, 0.6f, 2.f);
	return EBTNodeResult::InProgress;
}

void UBTTask_GuardLookAround::TickTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory, float DeltaSeconds)
{
	AAIController* AI = OwnerComp.GetAIOwner();
	ASecurityGuard* Guard = AI ? Cast<ASecurityGuard>(AI->GetPawn()) : nullptr;
	if (!Guard || Guard->IsDead())
	{
		FinishLatentTask(OwnerComp, EBTNodeResult::Failed);
		return;
	}
	const float Now = OwnerComp.GetWorld()->GetTimeSeconds();
	if (Now < PhaseEnd)
	{
		return;
	}

	// look left, look right, then face the original direction - the body turns smoothly at the guard's turn rate
	static const float Offsets[] = {-1.f, 1.f, 0.f};
	if (Phase < 3)
	{
		const float Yaw = BaseYaw + Offsets[Phase] * LookAngle * FMath::FRandRange(0.8f, 1.15f);
		const FVector Dir = FRotator(0.f, Yaw, 0.f).Vector();
		AI->SetFocalPoint(Origin + Dir * 500.f + FVector(0.f, 0.f, 50.f), EAIFocusPriority::Gameplay);
		PhaseEnd = Now + (Phase == 2 ? LookTime * 0.6f : LookTime);
		++Phase;
		return;
	}

	// done: decide where to go next
	AI->ClearFocus(EAIFocusPriority::Gameplay);
	if (UBlackboardComponent* BB = OwnerComp.GetBlackboardComponent())
	{
		if (bPickNextPatrolPoint)
		{
			BB->SetValueAsVector(GuardKeys::PatrolPoint, Guard->PickPatrolLocation());
		}
		if (bForgetLastKnown)
		{
			BB->SetValueAsBool(GuardKeys::HasLastKnown, false);
		}
	}
	FinishLatentTask(OwnerComp, EBTNodeResult::Succeeded);
}

EBTNodeResult::Type UBTTask_GuardLookAround::AbortTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory)
{
	if (AAIController* AI = OwnerComp.GetAIOwner())
	{
		AI->ClearFocus(EAIFocusPriority::Gameplay);
	}
	return EBTNodeResult::Aborted;
}

FString UBTTask_GuardLookAround::GetStaticDescription() const
{
	return FString::Printf(TEXT("look +-%.0f deg, %.1f s each%s%s"), LookAngle, LookTime,
	                       bPickNextPatrolPoint ? TEXT(", then pick next patrol point") : TEXT(""),
	                       bForgetLastKnown ? TEXT(", then give up the search") : TEXT(""));
}
