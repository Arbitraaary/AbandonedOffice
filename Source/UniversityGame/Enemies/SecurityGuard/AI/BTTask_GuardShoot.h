// Guard fires a short aimed burst at TargetActor (minor damage - BP_GuardBullet), then pauses before the next burst.

#pragma once

#include "CoreMinimal.h"
#include "BehaviorTree/BTTaskNode.h"
#include "BTTask_GuardShoot.generated.h"

UCLASS(meta = (DisplayName = "Guard Shoot Burst"))
class UNIVERSITYGAME_API UBTTask_GuardShoot : public UBTTaskNode
{
	GENERATED_BODY()

public:
	UBTTask_GuardShoot();

	UPROPERTY(EditAnywhere, Category = Shoot)
	int32 ShotsPerBurst = 4;

	// seconds between shots of a burst
	UPROPERTY(EditAnywhere, Category = Shoot)
	float ShotInterval = 0.22f;

	// pause after the burst
	UPROPERTY(EditAnywhere, Category = Shoot)
	float PauseAfterBurst = 0.9f;

protected:
	virtual EBTNodeResult::Type ExecuteTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory) override;
	virtual void TickTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory, float DeltaSeconds) override;
	virtual FString GetStaticDescription() const override;

private:
	// one node instance per guard (bCreateNodeInstance)
	int32 ShotsLeft = 0;
	float NextShot = 0.f;
	float EndTime = 0.f;
};
