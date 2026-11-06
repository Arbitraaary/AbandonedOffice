#include "PickupMessageOverlay.h"

#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

double FPickupMessageOverlay::Now() const
{
	const UWorld* World = WorldPtr.Get();
	return World ? World->GetTimeSeconds() : 0.0;
}

const FPickupMessageOverlay::FMessage* FPickupMessageOverlay::GetActive(const int32 Index) const
{
	const double T = Now();
	int32 Seen = 0;
	for (int32 i = Messages.Num() - 1; i >= 0; --i)          // newest first
	{
		if (Messages[i].ShowUntil > T)
		{
			if (Seen == Index) return &Messages[i];
			++Seen;
		}
	}
	return nullptr;
}

void FPickupMessageOverlay::Attach(UWorld* World)
{
	if (Root.IsValid() || World == nullptr) return;
	UGameViewportClient* Viewport = World->GetGameViewport();
	if (Viewport == nullptr) return;
	WorldPtr = World;

	TSharedRef<SVerticalBox> Lines = SNew(SVerticalBox);
	TWeakPtr<FPickupMessageOverlay> Weak = AsShared();
	for (int32 i = 0; i < MaxLines; ++i)
	{
		auto Alpha = [Weak, i]() -> float
		{
			const TSharedPtr<FPickupMessageOverlay> Self = Weak.Pin();
			const FMessage* M = Self.IsValid() ? Self->GetActive(i) : nullptr;
			return M ? FMath::Clamp(static_cast<float>((M->ShowUntil - Self->Now()) / FadeSeconds), 0.f, 1.f) : 0.f;
		};
		Lines->AddSlot()
		.AutoHeight()
		.HAlign(HAlign_Center)
		.Padding(0.f, 2.f)
		[
			SNew(STextBlock)
			.Font(FCoreStyle::GetDefaultFontStyle("Bold", 20))
			.ShadowOffset(FVector2D(1.5f, 1.5f))
			.Text_Lambda([Weak, i]() -> FText
			{
				const TSharedPtr<FPickupMessageOverlay> Self = Weak.Pin();
				const FMessage* M = Self.IsValid() ? Self->GetActive(i) : nullptr;
				return M ? M->Text : FText::GetEmpty();
			})
			.ColorAndOpacity_Lambda([Weak, i, Alpha]() -> FSlateColor
			{
				const TSharedPtr<FPickupMessageOverlay> Self = Weak.Pin();
				const FMessage* M = Self.IsValid() ? Self->GetActive(i) : nullptr;
				FLinearColor C = M ? M->Color : FLinearColor::Transparent;
				C.A = Alpha();
				return FSlateColor(C);
			})
			.ShadowColorAndOpacity_Lambda([Alpha]() -> FLinearColor
			{
				return FLinearColor(0.f, 0.f, 0.f, 0.85f * Alpha());
			})
		];
	}

	// countdown (bulletproof vest): big enough to notice, blinks during the last 3 seconds
	Lines->AddSlot()
	.AutoHeight()
	.HAlign(HAlign_Center)
	.Padding(0.f, 10.f, 0.f, 0.f)
	[
		SNew(STextBlock)
		.Font(FCoreStyle::GetDefaultFontStyle("Bold", 22))
		.ShadowOffset(FVector2D(1.5f, 1.5f))
		.ShadowColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.85f))
		.Text_Lambda([Weak]() -> FText
		{
			const TSharedPtr<FPickupMessageOverlay> Self = Weak.Pin();
			if (!Self.IsValid()) return FText::GetEmpty();
			const double Left = Self->CountdownEnd - Self->Now();
			if (Left <= 0.0) return FText::GetEmpty();
			return FText::FromString(FString::Printf(TEXT("%s  %d s"), *Self->CountdownLabel, FMath::CeilToInt(Left)));
		})
		.ColorAndOpacity_Lambda([Weak]() -> FSlateColor
		{
			const TSharedPtr<FPickupMessageOverlay> Self = Weak.Pin();
			if (!Self.IsValid()) return FSlateColor(FLinearColor::Transparent);
			const double Left = Self->CountdownEnd - Self->Now();
			FLinearColor C = Self->CountdownColor;
			if (Left <= 0.0) C.A = 0.f;
			else if (Left < 3.0) C.A = 0.45f + 0.55f * FMath::Abs(FMath::Cos(static_cast<float>(Left) * PI * 2.f));
			return FSlateColor(C);
		})
	];

	Root = SNew(SBox)
		.HAlign(HAlign_Center)
		.VAlign(VAlign_Center)
		.Padding(FMargin(0.f, 230.f, 0.f, 0.f))          // a bit below the crosshair
		.Visibility(EVisibility::HitTestInvisible)
		[
			Lines
		];
	Viewport->AddViewportWidgetContent(Root.ToSharedRef(), 20);
}

void FPickupMessageOverlay::Show(UWorld* World, const FText& Text, const FLinearColor& Color, const float Seconds)
{
	Attach(World);
	const double T = Now();
	Messages.RemoveAll([T](const FMessage& M) { return M.ShowUntil <= T; });
	if (Messages.Num() >= MaxLines)
	{
		Messages.RemoveAt(0);
	}
	Messages.Add({Text, Color, T + Seconds});
}

void FPickupMessageOverlay::ShowCountdown(UWorld* World, const FString& Label, const FLinearColor& Color, const double EndTime)
{
	Attach(World);
	CountdownLabel = Label;
	CountdownColor = Color;
	CountdownEnd = EndTime;
}

void FPickupMessageOverlay::Detach()
{
	if (Root.IsValid())
	{
		if (UWorld* World = WorldPtr.Get())
		{
			if (UGameViewportClient* Viewport = World->GetGameViewport())
			{
				Viewport->RemoveViewportWidgetContent(Root.ToSharedRef());
			}
		}
		Root.Reset();
	}
	Messages.Reset();
	CountdownEnd = 0.0;
}
