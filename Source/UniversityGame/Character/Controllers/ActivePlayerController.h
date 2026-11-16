// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "InputMappingContext.h"
#include "ActivePlayerController.generated.h"

class UPlayerAmmoWidget;
class FGameOverOverlay;
class FDamageFlashOverlay;
class UHitCameraModifier;
class UPlayerHealthbarWidget;
class UInputMappingContext;
/**
 * 
 */
UCLASS()
class UNIVERSITYGAME_API AActivePlayerController : public APlayerController
{
	GENERATED_BODY()

protected:
	UPROPERTY(EditAnywhere, Category = Input)
	TSoftObjectPtr<UInputMappingContext> InputMapping;

	UPROPERTY(EditDefaultsOnly, Category = UI)
	TSubclassOf<UUserWidget> CrosshairClass;

	UPROPERTY()
	UUserWidget* CrosshairWidget;

	UPROPERTY(EditDefaultsOnly, Category = UI)
	TSubclassOf<UPlayerHealthbarWidget> PlayerHealthBarClass;

	UPROPERTY()
	UPlayerHealthbarWidget* PlayerHealthBarWidget;

	UPROPERTY(EditDefaultsOnly, Category = UI)
	TSubclassOf<UPlayerAmmoWidget> PlayerAmmoClass;

	UPROPERTY()
	UPlayerAmmoWidget* PlayerAmmoWidget;

	TSharedPtr<FGameOverOverlay> GameOverOverlay;

	TSharedPtr<FDamageFlashOverlay> DamageFlashOverlay;

	UPROPERTY()
	UHitCameraModifier* HitCameraModifier;

public:
	virtual void SetupInputComponent() override;

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	// pauses the game (enemies stop shooting) and shows the GAME OVER screen with RESTART / QUIT
	void ShowGameOver(const FText& Reason);

	bool IsGameOver() const;

	// the player was hit: camera jolt away from the shot + red tint over the screen
	void PlayHitReaction(const FVector& FromLocation, float Damage);

	virtual void BeginPlay() override;
	
	void ShowCrosshair();

	void HideCrosshair() const;

	void UpdateHealthPercentage(float Percentage);

	
	void UpdateGeneralAmmoCapacity(float Count);
	void UpdateUnequippedAmmoCount(float Count);
	void UpdateMagCapacity(float Count);
	void UpdateAmmoInMagCount(float Count);

private:

	void CreateHealthBar();
	void CreateAmmoWidget();
	void CreateCrosshair();	
};
