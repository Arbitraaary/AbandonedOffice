// Red translucent tint over the whole screen when the player is hit. Pure Slate, added to the game viewport.

#pragma once

#include "CoreMinimal.h"
#include "Layout/Visibility.h"

class SWidget;
class UWorld;
class APlayerController;
struct FSlateColor;

class UNIVERSITYGAME_API FDamageFlashOverlay : public TSharedFromThis<FDamageFlashOverlay>
{
public:
	void Attach(APlayerController* PC);

	void Detach();

	// Strength 0..1
	void Flash(float Strength);

private:
	float CurrentAlpha() const;
	FSlateColor GetTint() const;
	EVisibility GetTintVisibility() const;

	TSharedPtr<SWidget> Root;
	TWeakObjectPtr<UWorld> WorldPtr;
	double FlashAt = -100.0;
	float FlashStrength = 0.f;
};
