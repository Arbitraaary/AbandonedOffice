// Natural phenomenon 2: rain that starts and stops at random. Clear weather for a random while, then the rain
// sets in, pours for a random while and dies down again. The drops are instanced streaks falling round the
// player; every drop ends on the first surface under it, so there is no rain under a roof (inside the office).
// While it rains it gets darker and foggier (ADayNightCycle reads GetStrength) and now and then lightning flashes.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RainWeather.generated.h"

class UInstancedStaticMeshComponent;
class UDirectionalLightComponent;
class UMaterialInterface;

UCLASS()
class UNIVERSITYGAME_API ARainWeather : public AActor
{
	GENERATED_BODY()

public:
	ARainWeather();

	// random length of the dry spells and of the rain, seconds
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	FVector2D ClearTime = FVector2D(35.f, 90.f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	FVector2D RainTime = FVector2D(30.f, 70.f);

	// seconds for the rain to set in / die down
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	float RampTime = 8.f;

	// start with rain (handy to show it straight away)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	bool bStartRaining = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	int32 MaxDrops = 2500;

	// drops fall in a circle of this radius round the camera (cm)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	float Radius = 2200.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	float FallSpeed = 1100.f;

	// wind: horizontal drift of the drops, cm/s
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	FVector Wind = FVector(120.f, 60.f, 0.f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rain")
	UMaterialInterface* DropMaterial;

	// 0 = dry .. 1 = pouring
	UFUNCTION(BlueprintPure, Category = "Rain")
	float GetStrength() const { return Strength; }

	UFUNCTION(BlueprintPure, Category = "Rain")
	bool IsRaining() const { return Phase != EPhase::Clear; }

	virtual void Tick(float DeltaTime) override;

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, Category = "Rain")
	UInstancedStaticMeshComponent* Drops;

	// the lightning flash
	UPROPERTY(VisibleAnywhere, Category = "Rain")
	UDirectionalLightComponent* Lightning;

private:
	enum class EPhase : uint8 { Clear, Starting, Raining, Stopping };

	struct FDrop
	{
		FVector Pos = FVector::ZeroVector;
		float EndZ = 0.f;          // the surface it lands on
		bool bActive = false;
	};

	void UpdateWeather(float DeltaTime);
	void UpdateDrops(float DeltaTime);
	void UpdateLightning(float DeltaTime);
	void Respawn(FDrop& Drop, const FVector& Centre, bool bAnyHeight);
	FVector ViewCentre() const;

	TArray<FDrop> Pool;
	TArray<FTransform> Transforms;
	int32 ActiveDrops = 0;
	EPhase Phase = EPhase::Clear;
	float PhaseEnd = 0.f;
	float Strength = 0.f;
	float NextFlash = 0.f;
	float FlashTime = -1.f;
	int32 FlashStrikes = 0;
};
