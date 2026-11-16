// Guard stops, looks around (plays a "look around" idle and smoothly turns left and right),
// then chooses where to go next (PatrolPoint) and/or forgets the last known player position.

#pragma once

#include "CoreMinimal.h"
#include "BehaviorTree/BTTaskNode.h"
#include "BTTask_GuardLookAround.generated.h"

UCLASS(meta = (DisplayName = "Guard Look Around"))
class UNIVERSITYGAME_API UBTTask_GuardLookAround : public UBTTaskNode
{
	GENERATED_BODY()

public:
	UBTTask_GuardLookAround();

	// how far to the left and to the right he turns (degrees)
	UPROPERTY(EditAnywhere, Category = LookAround)
	float LookAngle = 70.f;

	// how long he looks in each direction (seconds)
	UPROPERTY(EditAnywhere, Category = LookAround)
	float LookTime = 1.1f;

	// after looking around: choose the next patrol point (writes PatrolPoint)
	UPROPERTY(EditAnywhere, Category = LookAround)
	bool bPickNextPatrolPoint = true;

	// after looking around: give up the search (clears HasLastKnown)
	UPROPERTY(EditAnywhere, Category = LookAround)
	bool bForgetLastKnown = false;

protected:
	virtual EBTNodeResult::Type ExecuteTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory) override;
	virtual void TickTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory, float DeltaSeconds) override;
	virtual EBTNodeResult::Type AbortTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory) override;
	virtual FString GetStaticDescription() const override;

private:
	// one node instance per guard (bCreateNodeInstance)
	FVector Origin = FVector::ZeroVector;
	float BaseYaw = 0.f;
	float PhaseEnd = 0.f;
	int32 Phase = 0;
};
