// Guard's senses, every 0.2 s: can he see the player, is the player in range of his rifle, where was he last seen.
// Also: run while hunting, walk while patrolling; look at the player while he sees him.

#pragma once

#include "CoreMinimal.h"
#include "BehaviorTree/BTService.h"
#include "BTService_GuardSenses.generated.h"

UCLASS(meta = (DisplayName = "Guard Senses"))
class UNIVERSITYGAME_API UBTService_GuardSenses : public UBTService
{
	GENERATED_BODY()

public:
	UBTService_GuardSenses();

protected:
	virtual void TickNode(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory, float DeltaSeconds) override;
	virtual FString GetStaticDescription() const override;

private:
	bool bWasSeeing = false;           // one node instance per guard (bCreateNodeInstance)
};
