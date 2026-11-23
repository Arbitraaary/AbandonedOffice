// Anim notify for the reload montage: placed where the left hand grabs the magazine (start of the "Loop" section) -
// the magazine leaves the weapon and follows the hand until the Reload Cycle notify puts it back.

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "AnimNotify_MagazineOut.generated.h"

UCLASS(meta = (DisplayName = "Magazine Out"))
class UNIVERSITYGAME_API UAnimNotify_MagazineOut : public UAnimNotify
{
	GENERATED_BODY()

public:
	virtual void Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
	                    const FAnimNotifyEventReference& EventReference) override;

	virtual FString GetNotifyName_Implementation() const override;
};
