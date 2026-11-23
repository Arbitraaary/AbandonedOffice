#include "AnimNotify_MagazineOut.h"

#include "Components/SkeletalMeshComponent.h"
#include "MainCharacter.h"

void UAnimNotify_MagazineOut::Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
                                     const FAnimNotifyEventReference& EventReference)
{
	Super::Notify(MeshComp, Animation, EventReference);
	if (AMainCharacter* Character = MeshComp ? Cast<AMainCharacter>(MeshComp->GetOwner()) : nullptr)
	{
		Character->OnMagazineOut();
	}
}

FString UAnimNotify_MagazineOut::GetNotifyName_Implementation() const
{
	return TEXT("MagazineOut");
}
