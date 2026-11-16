// Fill out your copyright notice in the Description page of Project Settings.


#include "ActivePlayerController.h"
#include "EnhancedInputSubsystems.h"
#include "NavigationSystemTypes.h"
#include "Blueprint/UserWidget.h"
#include "UniversityGame/HUD/PlayerAmmoWidget.h"
#include "UniversityGame/HUD/PlayerHealthbarWidget.h"
#include "UniversityGame/HUD/GameOverOverlay.h"
#include "UniversityGame/HUD/DamageFlashOverlay.h"
#include "UniversityGame/HUD/HitCameraModifier.h"
#include "Camera/PlayerCameraManager.h"


class UEnhancedInputLocalPlayerSubsystem;

void AActivePlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	
	if (ULocalPlayer* LocalPlayer = Cast<ULocalPlayer>(Player))
	{
		if (UEnhancedInputLocalPlayerSubsystem* InputSystem = LocalPlayer->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
		{
			if (!InputMapping.IsNull())
			{
				InputSystem->AddMappingContext(InputMapping.LoadSynchronous(), 0);
			}
		}
	}
}

void AActivePlayerController::BeginPlay()
{
	Super::BeginPlay();
	// a restart after GAME OVER keeps the viewport in UI mode with the cursor - give the game the input back
	SetInputMode(FInputModeGameOnly());
	bShowMouseCursor = false;
	CreateCrosshair();
	CreateHealthBar();
	CreateAmmoWidget();

	DamageFlashOverlay = MakeShared<FDamageFlashOverlay>();
	DamageFlashOverlay->Attach(this);
}

void AActivePlayerController::PlayHitReaction(const FVector& FromLocation, const float Damage)
{
	if (IsGameOver()) return;
	const float Strength = FMath::Clamp(Damage / 8.f, 0.5f, 1.f);

	if (DamageFlashOverlay.IsValid())
	{
		DamageFlashOverlay->Flash(Strength);
	}

	if (!HitCameraModifier && PlayerCameraManager)
	{
		HitCameraModifier = Cast<UHitCameraModifier>(PlayerCameraManager->AddNewCameraModifier(UHitCameraModifier::StaticClass()));
	}
	if (HitCameraModifier)
	{
		const FVector From = GetPawn() ? FromLocation - GetPawn()->GetActorLocation() : FVector::ForwardVector;
		HitCameraModifier->Kick(From, Strength);
	}
}

void AActivePlayerController::ShowGameOver(const FText& Reason)
{
	if (IsGameOver()) return;
	GameOverOverlay = MakeShared<FGameOverOverlay>();
	GameOverOverlay->Show(this, FText::FromString(TEXT("GAME OVER")), Reason);
	HideCrosshair();

	// freeze the world: enemies stop moving and shooting; the buttons still work (Slate runs while paused)
	SetPause(true);
	bShowMouseCursor = true;
	FInputModeUIOnly Mode;
	Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	SetInputMode(Mode);
}

bool AActivePlayerController::IsGameOver() const
{
	return GameOverOverlay.IsValid() && GameOverOverlay->IsShown();
}

void AActivePlayerController::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (GameOverOverlay.IsValid())
	{
		GameOverOverlay->Detach();
		GameOverOverlay.Reset();
	}
	if (DamageFlashOverlay.IsValid())
	{
		DamageFlashOverlay->Detach();
		DamageFlashOverlay.Reset();
	}
	Super::EndPlay(EndPlayReason);
}

void AActivePlayerController::CreateCrosshair()
{

	if (CrosshairClass != nullptr)
	{
		if (CrosshairWidget = CreateWidget<UUserWidget>(this, CrosshairClass, TEXT("Crosshair")); CrosshairWidget != nullptr)
		{
			CrosshairWidget->AddToViewport();
		}
	}
}

void AActivePlayerController::ShowCrosshair()
{
	if (CrosshairWidget == nullptr)
	{
		CreateCrosshair();
	}else if (!CrosshairWidget->IsInViewport())
	{
		CrosshairWidget->AddToViewport();
	}
}

void AActivePlayerController::HideCrosshair() const
{
	if (CrosshairWidget != nullptr && CrosshairWidget->IsInViewport())
	{
		CrosshairWidget->RemoveFromParent();
	}
}

void AActivePlayerController::UpdateHealthPercentage(float Percentage)
{
	if (PlayerHealthBarWidget != nullptr)
	{
		PlayerHealthBarWidget->UpdateHealthPercentage(Percentage);
	}
}

void AActivePlayerController::UpdateGeneralAmmoCapacity(float Count)
{
	if (PlayerAmmoWidget != nullptr)
	{
		PlayerAmmoWidget->UpdateGeneralAmmoCapacity(Count);
	}
}

void AActivePlayerController::UpdateUnequippedAmmoCount(float Count)
{
	if (PlayerAmmoWidget != nullptr)
	{
		PlayerAmmoWidget->UpdateUnequippedAmmoCount(Count);
	}
}

void AActivePlayerController::UpdateMagCapacity(float Count)
{
	if (PlayerAmmoWidget != nullptr)
	{
		PlayerAmmoWidget->UpdateMagCapacity(Count);
	}
}

void AActivePlayerController::UpdateAmmoInMagCount(float Count)
{
	if (PlayerAmmoWidget != nullptr)
	{
		PlayerAmmoWidget->UpdateAmmoInMagCount(Count);
	}
}

void AActivePlayerController::CreateHealthBar()
{
	
	if (PlayerHealthBarClass != nullptr)
	{
		if (PlayerHealthBarWidget = CreateWidget<UPlayerHealthbarWidget>(this, PlayerHealthBarClass, TEXT("PlayerHealthBar")); PlayerHealthBarWidget != nullptr)
		{
			PlayerHealthBarWidget->AddToViewport();
		}
	}
}

void AActivePlayerController::CreateAmmoWidget()
{
	
	if (PlayerAmmoClass != nullptr)
	{
		if (PlayerAmmoWidget = CreateWidget<UPlayerAmmoWidget>(this, PlayerAmmoClass, TEXT("PlayerAmmoWidget")); PlayerAmmoWidget != nullptr)
		{
			PlayerAmmoWidget->AddToViewport();
		}
	}
}
