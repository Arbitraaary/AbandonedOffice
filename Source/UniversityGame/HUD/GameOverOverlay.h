// "GAME OVER" screen: darkens the game, big red title, the reason (out of health / out of ammo),
// RESTART and QUIT buttons. Pure Slate, added straight to the game viewport - needs no widget blueprint,
// keeps working while the game is paused.

#pragma once

#include "CoreMinimal.h"

class SWidget;
class UWorld;
class APlayerController;

class UNIVERSITYGAME_API FGameOverOverlay : public TSharedFromThis<FGameOverOverlay>
{
public:
	void Show(APlayerController* PC, const FText& Title, const FText& Reason);

	void Detach();

	bool IsShown() const { return Root.IsValid(); }

private:
	float Fade() const;                        // 0 -> 1 during the first half second

	TSharedPtr<SWidget> Root;
	TWeakObjectPtr<UWorld> WorldPtr;
	TWeakObjectPtr<APlayerController> PCPtr;
	double ShownAt = 0.0;
};
