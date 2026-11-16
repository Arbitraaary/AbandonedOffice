// AI controller of the security guard: sight perception + BT_SecurityGuard.
// Blackboard keys (BB_SecurityGuard): TargetActor (Object), CanSeeTarget (Bool), InAttackRange (Bool),
// HasLastKnown (Bool), LastKnownLocation (Vector), PatrolPoint (Vector).
//
// BT_SecurityGuard:
//   ROOT -> Selector  [service: Guard Senses]
//     1 Sequence "Attack"  [Blackboard: InAttackRange is set, aborts Both]           -> Guard Shoot Burst
//     2 Sequence "Hunt"    [Blackboard: HasLastKnown is set, aborts Lower Priority]  -> Move To LastKnownLocation
//                                                                                    -> Guard Look Around (forget)
//     3 Sequence "Patrol"                                                            -> Move To PatrolPoint
//                                                                                    -> Guard Look Around (pick next)

#pragma once

#include "CoreMinimal.h"
#include "AIController.h"
#include "Perception/AIPerceptionTypes.h"
#include "SecurityGuardAIController.generated.h"

class UAISenseConfig_Sight;

namespace GuardKeys
{
	const FName TargetActor(TEXT("TargetActor"));
	const FName CanSeeTarget(TEXT("CanSeeTarget"));
	const FName InAttackRange(TEXT("InAttackRange"));
	const FName HasLastKnown(TEXT("HasLastKnown"));
	const FName LastKnownLocation(TEXT("LastKnownLocation"));
	const FName PatrolPoint(TEXT("PatrolPoint"));
}

UCLASS()
class UNIVERSITYGAME_API ASecurityGuardAIController : public AAIController
{
	GENERATED_BODY()

public:
	ASecurityGuardAIController();

	virtual void OnPossess(APawn* InPawn) override;

	virtual FGenericTeamId GetGenericTeamId() const override;

	virtual ETeamAttitude::Type GetTeamAttitudeTowards(const AActor& Other) const override;

	// a shot flew past / hit him: he knows where the shooter is even without seeing him
	void ReportThreat(AActor* Threat);

	// is the actor visible to the guard right now (perception + not hidden in smoke)?
	bool CanSee(const AActor* Actor) const;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = AI)
	UAIPerceptionComponent* Perception;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = AI)
	UAISenseConfig_Sight* Sight;

	UFUNCTION()
	void OnTargetPerceived(AActor* Actor, FAIStimulus Stimulus);
};
