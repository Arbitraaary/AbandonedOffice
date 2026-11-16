#include "DamageFlashOverlay.h"

#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Layout/SBorder.h"

namespace DamageFlash
{
	const FLinearColor Red(0.8f, 0.02f, 0.02f, 1.f);
	constexpr float MaxAlpha = 0.35f;     // the scene stays visible under the tint
	constexpr double RiseTime = 0.06;
	constexpr double FadeTime = 0.6;
	constexpr int32 ZOrder = 5;           // under the HUD widgets (health, ammo) and the GAME OVER screen
}

void FDamageFlashOverlay::Attach(APlayerController* PC)
{
	UWorld* World = PC ? PC->GetWorld() : nullptr;
	UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
	if (Root.IsValid() || !Viewport) return;
	WorldPtr = World;

	Root = SNew(SBorder)
		.BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
		.BorderBackgroundColor(TAttribute<FSlateColor>::CreateSP(this, &FDamageFlashOverlay::GetTint))
		.Visibility(TAttribute<EVisibility>::CreateSP(this, &FDamageFlashOverlay::GetTintVisibility));

	Viewport->AddViewportWidgetContent(Root.ToSharedRef(), DamageFlash::ZOrder);
}

void FDamageFlashOverlay::Detach()
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

void FDamageFlashOverlay::Flash(const float Strength)
{
	FlashStrength = FMath::Clamp(Strength, 0.f, 1.f);
	FlashAt = FPlatformTime::Seconds();
}

float FDamageFlashOverlay::CurrentAlpha() const
{
	const double T = FPlatformTime::Seconds() - FlashAt;
	if (T < 0.0 || T > DamageFlash::RiseTime + DamageFlash::FadeTime) return 0.f;
	const double K = T < DamageFlash::RiseTime ? T / DamageFlash::RiseTime
	                                           : 1.0 - (T - DamageFlash::RiseTime) / DamageFlash::FadeTime;
	return DamageFlash::MaxAlpha * FlashStrength * static_cast<float>(K);
}

FSlateColor FDamageFlashOverlay::GetTint() const
{
	return FSlateColor(DamageFlash::Red.CopyWithNewOpacity(CurrentAlpha()));
}

EVisibility FDamageFlashOverlay::GetTintVisibility() const
{
	return CurrentAlpha() > 0.001f ? EVisibility::HitTestInvisible : EVisibility::Collapsed;
}
