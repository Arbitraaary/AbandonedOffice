#include "AnimNotify_ReloadCycle.h"

#include "Components/SkeletalMeshComponent.h"
#include "MainCharacter.h"

void UAnimNotify_ReloadCycle::Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
                                     const FAnimNotifyEventReference& EventReference)
{
	Super::Notify(MeshComp, Animation, EventReference);
	if (AMainCharacter* Character = MeshComp ? Cast<AMainCharacter>(MeshComp->GetOwner()) : nullptr)
	{
		Character->OnReloadCycle();
	}
}

FString UAnimNotify_ReloadCycle::GetNotifyName_Implementation() const
{
	return TEXT("ReloadCycle");
}
