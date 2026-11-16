// Health bar of the security guard: a thin solid blue bar drawn in C++ (no UMG asset needed).
// Same behaviour as the soldiers' bar (it simply shrinks), but thinner and blue, so guards are easy to tell apart.
// Feedback for the player: the bar flashes white when the guard is hit; short messages pop up above it
// ("DODGE 63%", "SHOCKED!", "BLINDED", "LOST YOU").

#pragma once

#include "CoreMinimal.h"
#include "UniversityGame/Enemies/EnemyHealthBarWidget.h"
#include "GuardHealthBarWidget.generated.h"

UCLASS()
class UNIVERSITYGAME_API UGuardHealthBarWidget : public UEnemyHealthBarWidget
{
	GENERATED_BODY()

public:
	// bar size in pixels; the widget is taller so the "DODGE" text fits above the bar
	static constexpr float Width = 150.f;
	static constexpr float Height = 10.f;
	static constexpr float TotalHeight = 34.f;

	void Flash();

	// Chance: the dodge probability that was rolled (shown as a percentage)
	void ShowDodge(float Chance);

	// a short message above the bar ("BLINDED", "SHOCKED!", "LOST YOU") for Seconds
	void ShowStatus(const FString& Text, const FLinearColor& Color, float Seconds = 1.2f);

protected:
	virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	                          FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle,
	                          bool bParentEnabled) const override;

private:
	double Now() const;

	double FlashStart = -100.0;
	double StatusStart = -100.0;
	double StatusTime = 1.0;
	FString StatusText;
	FLinearColor StatusColor = FLinearColor::White;
};
