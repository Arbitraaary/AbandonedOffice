#include "BTService_GuardSenses.h"

#include "SecurityGuardAIController.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "UniversityGame/Enemies/SecurityGuard/SecurityGuard.h"
#include "UniversityGame/Environment/Hazards/SmokeZone.h"

UBTService_GuardSenses::UBTService_GuardSenses()
{
	NodeName = TEXT("Guard Senses");
	Interval = 0.2f;
	RandomDeviation = 0.05f;
	bNotifyTick = true;
	bCreateNodeInstance = true;
}

void UBTService_GuardSenses::TickNode(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory, float DeltaSeconds)
{
	Super::TickNode(OwnerComp, NodeMemory, DeltaSeconds);

	ASecurityGuardAIController* AI = Cast<ASecurityGuardAIController>(OwnerComp.GetAIOwner());
	UBlackboardComponent* BB = OwnerComp.GetBlackboardComponent();
	ASecurityGuard* Guard = AI ? Cast<ASecurityGuard>(AI->GetPawn()) : nullptr;
	if (!AI || !BB || !Guard || Guard->IsDead())
	{
		return;
	}

	const AActor* Target = Cast<AActor>(BB->GetValueAsObject(GuardKeys::TargetActor));
	const bool bSees = Target && AI->CanSee(Target) && AI->LineOfSightTo(Target);
	const bool bInRange = bSees && FVector::Dist(Guard->GetActorLocation(), Target->GetActorLocation()) <= Guard->AttackRange;

	BB->SetValueAsBool(GuardKeys::CanSeeTarget, bSees);
	BB->SetValueAsBool(GuardKeys::InAttackRange, bInRange);
	if (bSees)
	{
		BB->SetValueAsVector(GuardKeys::LastKnownLocation, Target->GetActorLocation());
		BB->SetValueAsBool(GuardKeys::HasLastKnown, true);
		AI->SetFocus(const_cast<AActor*>(Target), EAIFocusPriority::Gameplay);   // keeps facing the player (smooth turn)
	}
	else if (bWasSeeing)
	{
		AI->ClearFocus(EAIFocusPriority::Gameplay);
		if (Target && ASmokeZone::IsActorInSmoke(Target))
		{
			Guard->ShowStatus(TEXT("LOST YOU"), FLinearColor(1.f, 0.6f, 0.2f), 1.5f);   // the player vanished in the smoke
		}
	}
	bWasSeeing = bSees;

	// running while hunting the player, walking while patrolling
	Guard->SetRunning(bSees || BB->GetValueAsBool(GuardKeys::HasLastKnown));
}

FString UBTService_GuardSenses::GetStaticDescription() const
{
	return TEXT("CanSeeTarget, InAttackRange, LastKnownLocation; run / walk; face the player");
}
