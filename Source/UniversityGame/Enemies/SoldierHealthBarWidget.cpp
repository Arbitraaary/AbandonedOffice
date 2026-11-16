#include "SoldierHealthBarWidget.h"

#include "Brushes/SlateColorBrush.h"
#include "Rendering/DrawElements.h"

namespace SoldierBarDraw
{
	const FLinearColor Outline(0.02f, 0.f, 0.f, 0.95f);
	const FLinearColor Back(0.12f, 0.01f, 0.01f, 0.75f);
	const FLinearColor Fill(0.8f, 0.03f, 0.02f, 1.f);

	void Box(const FGeometry& G, FSlateWindowElementList& Out, int32 Layer, float X, float Y, float W, float H, const FLinearColor& C)
	{
		static const FSlateColorBrush White(FLinearColor::White);
		if (W <= 0.f || H <= 0.f) return;
		FSlateDrawElement::MakeBox(Out, Layer, G.ToPaintGeometry(FVector2f(W, H), FSlateLayoutTransform(FVector2f(X, Y))),
		                           &White, ESlateDrawEffect::None, C);
	}
}

int32 USoldierHealthBarWidget::NativePaint(const FPaintArgs& Args, const FGeometry& G, const FSlateRect& MyCullingRect,
                                           FSlateWindowElementList& Out, int32 LayerId, const FWidgetStyle& InWidgetStyle,
                                           bool bParentEnabled) const
{
	using namespace SoldierBarDraw;
	const int32 L = Super::NativePaint(Args, G, MyCullingRect, Out, LayerId, InWidgetStyle, bParentEnabled) + 1;
	const float Pct = FMath::Clamp(HealthPercentage, 0.f, 1.f);
	const FVector2f Size = G.GetLocalSize();
	const float W = Size.X > 1.f ? Size.X : Width;
	const float H = Size.Y > 1.f ? Size.Y : Height;
	Box(G, Out, L, 0.f, 0.f, W, H, Outline);
	Box(G, Out, L + 1, 1.f, 1.f, W - 2.f, H - 2.f, Back);
	Box(G, Out, L + 2, 1.f, 1.f, (W - 2.f) * Pct, H - 2.f, Fill);
	return L + 2;
}
