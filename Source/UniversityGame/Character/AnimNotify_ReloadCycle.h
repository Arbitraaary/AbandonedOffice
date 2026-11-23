// Anim notify for the reload montage: placed at the end of the "Loop" section,
// fires once per cycle of putting rounds in -> the character loads a few rounds and decides whether to finish.

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "AnimNotify_ReloadCycle.generated.h"

UCLASS(meta = (DisplayName = "Reload Cycle"))
class UNIVERSITYGAME_API UAnimNotify_ReloadCycle : public UAnimNotify
{
	GENERATED_BODY()

public:
	virtual void Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
	                    const FAnimNotifyEventReference& EventReference) override;

	virtual FString GetNotifyName_Implementation() const override;
};
