// Small on-screen pickup messages ("+15 HEALTH", "+15 AMMO", "BULLETPROOF FOR 15 S").
// Pure Slate, added straight to the game viewport - needs no widget blueprint.
// Up to 3 lines under the crosshair, newest on top, each fades out at the end.

#pragma once

#include "CoreMinimal.h"

class SWidget;
class UWorld;

class UNIVERSITYGAME_API FPickupMessageOverlay : public TSharedFromThis<FPickupMessageOverlay>
{
public:
	void Show(UWorld* World, const FText& Text, const FLinearColor& Color, float Seconds = 2.5f);

	// a line that stays on screen and counts down until EndTime (world time seconds), e.g. "BULLETPROOF  12 s"
	void ShowCountdown(UWorld* World, const FString& Label, const FLinearColor& Color, double EndTime);

	// remove from the viewport (call from EndPlay)
	void Detach();

private:
	struct FMessage
	{
		FText Text;
		FLinearColor Color;
		double ShowUntil = 0.0;
	};

	void Attach(UWorld* World);
	const FMessage* GetActive(int32 Index) const;
	double Now() const;

	TArray<FMessage> Messages;

	FString CountdownLabel;
	FLinearColor CountdownColor = FLinearColor::White;
	double CountdownEnd = 0.0;
	TSharedPtr<SWidget> Root;
	TWeakObjectPtr<UWorld> WorldPtr;

	static constexpr int32 MaxLines = 3;
	static constexpr double FadeSeconds = 0.5;
};
