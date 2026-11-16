// Health bar of the soldiers: a thin solid red bar drawn in C++, sized exactly to the bar,
// so it can be pinned right above the head (the old widget blueprint was a 500x500 canvas).

#pragma once

#include "CoreMinimal.h"
#include "EnemyHealthBarWidget.h"
#include "SoldierHealthBarWidget.generated.h"

UCLASS()
class UNIVERSITYGAME_API USoldierHealthBarWidget : public UEnemyHealthBarWidget
{
	GENERATED_BODY()

public:
	static constexpr float Width = 100.f;
	static constexpr float Height = 8.f;

protected:
	virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	                          FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle,
	                          bool bParentEnabled) const override;
};
