#include "GuardHealthBarWidget.h"

#include "Brushes/SlateColorBrush.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"

namespace GuardBarDraw
{
	const FLinearColor Outline(0.005f, 0.01f, 0.03f, 0.95f);
	const FLinearColor Back(0.02f, 0.03f, 0.07f, 0.7f);
	const FLinearColor Fill(0.05f, 0.35f, 1.0f, 1.f);
	const FLinearColor DodgeColor(0.35f, 0.75f, 1.0f, 1.f);
	constexpr double FlashTime = 0.25;

	void Box(const FGeometry& G, FSlateWindowElementList& Out, int32 Layer, float X, float Y, float W, float H, const FLinearColor& C)
	{
		static const FSlateColorBrush White(FLinearColor::White);
		if (W <= 0.f || H <= 0.f) return;
		FSlateDrawElement::MakeBox(Out, Layer, G.ToPaintGeometry(FVector2f(W, H), FSlateLayoutTransform(FVector2f(X, Y))),
		                           &White, ESlateDrawEffect::None, C);
	}
}

double UGuardHealthBarWidget::Now() const
{
	return FSlateApplication::IsInitialized() ? FSlateApplication::Get().GetCurrentTime() : 0.0;
}

void UGuardHealthBarWidget::Flash()
{
	FlashStart = Now();
}

void UGuardHealthBarWidget::ShowDodge(const float Chance)
{
	ShowStatus(FString::Printf(TEXT("DODGE %d%%"), FMath::RoundToInt(Chance * 100.f)), GuardBarDraw::DodgeColor, 1.f);
}

void UGuardHealthBarWidget::ShowStatus(const FString& Text, const FLinearColor& Color, const float Seconds)
{
	StatusStart = Now();
	StatusTime = FMath::Max(Seconds, 0.2f);
	StatusText = Text;
	StatusColor = Color;
}

int32 UGuardHealthBarWidget::NativePaint(const FPaintArgs& Args, const FGeometry& G, const FSlateRect& MyCullingRect,
                                         FSlateWindowElementList& Out, int32 LayerId, const FWidgetStyle& InWidgetStyle,
                                         bool bParentEnabled) const
{
	using namespace GuardBarDraw;
	const int32 L = Super::NativePaint(Args, G, MyCullingRect, Out, LayerId, InWidgetStyle, bParentEnabled) + 1;
	const float Pct = FMath::Clamp(HealthPercentage, 0.f, 1.f);
	const double T = Now();

	// the bar sits at the bottom of the widget: 1 px dark outline, dark background, solid blue fill
	const FVector2f Size = G.GetLocalSize();
	const float W = Size.X > 1.f ? Size.X : Width;
	const float Y0 = (Size.Y > 1.f ? Size.Y : TotalHeight) - Height;
	const float Flash01 = static_cast<float>(FMath::Clamp(1.0 - (T - FlashStart) / FlashTime, 0.0, 1.0));
	Box(G, Out, L, 0.f, Y0, W, Height, FMath::Lerp(Outline, FLinearColor::White, Flash01));
	Box(G, Out, L + 1, 1.f, Y0 + 1.f, W - 2.f, Height - 2.f, Back);
	Box(G, Out, L + 2, 1.f, Y0 + 1.f, (W - 2.f) * Pct, Height - 2.f, FMath::Lerp(Fill, FLinearColor::White, Flash01));

	// a message above the bar ("DODGE 63%", "SHOCKED!"...): pops up, rises a little and fades out
	const double Age = T - StatusStart;
	if (Age >= 0.0 && Age < StatusTime && !StatusText.IsEmpty())
	{
		const float A = static_cast<float>(FMath::Min(1.0, 3.0 * (1.0 - Age / StatusTime)));
		const FSlateFontInfo Font = FCoreStyle::GetDefaultFontStyle("Bold", 13);
		const FString& Text = StatusText;
		const auto Measured = FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Text, Font);
		const FVector2f TextSize(static_cast<float>(Measured.X), static_cast<float>(Measured.Y));
		const float X = (W - TextSize.X) * 0.5f;
		const float Y = Y0 - TextSize.Y - 2.f - static_cast<float>(FMath::Min(Age, 1.0)) * 3.f;
		FLinearColor Shadow = Outline;
		Shadow.A = A;
		FLinearColor Ink = StatusColor;
		Ink.A = A;
		FSlateDrawElement::MakeText(Out, L + 3, G.ToPaintGeometry(TextSize, FSlateLayoutTransform(FVector2f(X + 1.f, Y + 1.f))),
		                            Text, Font, ESlateDrawEffect::None, Shadow);
		FSlateDrawElement::MakeText(Out, L + 4, G.ToPaintGeometry(TextSize, FSlateLayoutTransform(FVector2f(X, Y))),
		                            Text, Font, ESlateDrawEffect::None, Ink);
	}
	return L + 4;
}
