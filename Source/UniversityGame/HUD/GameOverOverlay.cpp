#include "GameOverOverlay.h"

#include "Brushes/SlateColorBrush.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace GameOverStyle
{
	const FLinearColor Red(0.85f, 0.06f, 0.04f, 1.f);
	const FLinearColor Panel(0.02f, 0.02f, 0.025f, 0.82f);

	const FSlateBrush* White()
	{
		static const FSlateColorBrush Brush(FLinearColor::White);
		return &Brush;
	}
}

float FGameOverOverlay::Fade() const
{
	const double Now = FSlateApplication::IsInitialized() ? FSlateApplication::Get().GetCurrentTime() : ShownAt + 1.0;
	return FMath::Clamp(static_cast<float>((Now - ShownAt) / 0.5), 0.f, 1.f);
}

void FGameOverOverlay::Show(APlayerController* PC, const FText& Title, const FText& Reason)
{
	UWorld* World = PC ? PC->GetWorld() : nullptr;
	UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
	if (Root.IsValid() || !Viewport) return;
	WorldPtr = World;
	PCPtr = PC;
	ShownAt = FSlateApplication::IsInitialized() ? FSlateApplication::Get().GetCurrentTime() : 0.0;

	using namespace GameOverStyle;
	TWeakPtr<FGameOverOverlay> Weak = AsShared();
	auto Faded = [Weak](const FLinearColor& C)
	{
		const TSharedPtr<FGameOverOverlay> Self = Weak.Pin();
		FLinearColor Out = C;
		Out.A *= Self.IsValid() ? Self->Fade() : 1.f;
		return Out;
	};

	auto MakeButton = [Faded](const FText& Label, TFunction<void()> OnClick, const FLinearColor& Tint)
	{
		return SNew(SBox)
			.WidthOverride(220.f)
			.HeightOverride(56.f)
			.Padding(10.f, 0.f)
			[
				SNew(SButton)
				.ButtonColorAndOpacity_Lambda([Faded, Tint]() { return FSlateColor(Faded(Tint)); })
				.HAlign(HAlign_Center)
				.VAlign(VAlign_Center)
				.OnClicked_Lambda([OnClick]() { OnClick(); return FReply::Handled(); })
				[
					SNew(STextBlock)
					.Text(Label)
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 20))
					.ColorAndOpacity_Lambda([Faded]() { return FSlateColor(Faded(FLinearColor::White)); })
				]
			];
	};

	TWeakObjectPtr<UWorld> WeakWorld = World;
	TWeakObjectPtr<APlayerController> WeakPC = PC;
	auto Restart = [WeakWorld, WeakPC]()
	{
		if (APlayerController* P = WeakPC.Get())
		{
			P->SetInputMode(FInputModeGameOnly());       // movement and shooting work again after the reload
			P->bShowMouseCursor = false;
			P->SetPause(false);
		}
		if (UWorld* W = WeakWorld.Get())
		{
			UGameplayStatics::OpenLevel(W, FName(*UGameplayStatics::GetCurrentLevelName(W)));
		}
	};
	auto Quit = [WeakWorld, WeakPC]()
	{
		if (UWorld* W = WeakWorld.Get())
		{
			UKismetSystemLibrary::QuitGame(W, WeakPC.Get(), EQuitPreference::Quit, false);
		}
	};

	Root = SNew(SOverlay)
		// the whole game darkens
		+ SOverlay::Slot()
		[
			SNew(SBorder)
			.BorderImage(White())
			.BorderBackgroundColor_Lambda([Faded]() { return FSlateColor(Faded(FLinearColor(0.f, 0.f, 0.f, 0.55f))); })
		]
		// a dark band across the screen with the title, the reason and the buttons
		+ SOverlay::Slot()
		.VAlign(VAlign_Center)
		[
			SNew(SBorder)
			.BorderImage(White())
			.BorderBackgroundColor_Lambda([Faded]() { return FSlateColor(Faded(Panel)); })
			.Padding(0.f, 28.f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
				[
					SNew(SBox).WidthOverride(640.f).HeightOverride(3.f)
					[
						SNew(SBorder).BorderImage(White())
						.BorderBackgroundColor_Lambda([Faded]() { return FSlateColor(Faded(Red)); })
					]
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 14.f, 0.f, 0.f)
				[
					SNew(STextBlock)
					.Text(Title)
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 84))
					.ColorAndOpacity_Lambda([Faded]() { return FSlateColor(Faded(Red)); })
					.ShadowOffset(FVector2D(3.f, 3.f))
					.ShadowColorAndOpacity_Lambda([Faded]() { return Faded(FLinearColor(0.f, 0.f, 0.f, 0.9f)); })
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 2.f, 0.f, 22.f)
				[
					SNew(STextBlock)
					.Text(Reason)
					.Font(FCoreStyle::GetDefaultFontStyle("Regular", 24))
					.ColorAndOpacity_Lambda([Faded]() { return FSlateColor(Faded(FLinearColor(0.9f, 0.9f, 0.9f, 1.f))); })
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth()
					[
						MakeButton(FText::FromString(TEXT("RESTART")), Restart, FLinearColor(0.75f, 0.08f, 0.05f, 1.f))
					]
					+ SHorizontalBox::Slot().AutoWidth()
					[
						MakeButton(FText::FromString(TEXT("QUIT")), Quit, FLinearColor(0.25f, 0.25f, 0.27f, 1.f))
					]
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 22.f, 0.f, 0.f)
				[
					SNew(SBox).WidthOverride(640.f).HeightOverride(3.f)
					[
						SNew(SBorder).BorderImage(White())
						.BorderBackgroundColor_Lambda([Faded]() { return FSlateColor(Faded(Red)); })
					]
				]
			]
		];

	Viewport->AddViewportWidgetContent(Root.ToSharedRef(), 1000);
}

void FGameOverOverlay::Detach()
{
	if (!Root.IsValid()) return;
	if (UWorld* World = WorldPtr.Get())
	{
		if (UGameViewportClient* Viewport = World->GetGameViewport())
		{
			Viewport->RemoveViewportWidgetContent(Root.ToSharedRef());
		}
	}
	Root.Reset();
}
