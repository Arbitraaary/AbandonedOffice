// Natural phenomenon 1: day and night. The sun (the level's directional light) goes round once every DayLength
// seconds; the classic BP_Sky_Sphere is refreshed so the sky follows it (dawn colours, night sky with stars),
// sun / sky light / fog / exposure change with the sun's height, a dim moon light takes over at night and
// the street lamps switch on (the broken ones only flicker weakly).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DayNightCycle.generated.h"

class ADirectionalLight;
class ASkyLight;
class AExponentialHeightFog;
class UDirectionalLightComponent;
class UPostProcessComponent;
class UStaticMeshComponent;
class UMaterialInterface;
class USpotLightComponent;
class ARainWeather;

UCLASS()
class UNIVERSITYGAME_API ADayNightCycle : public AActor
{
	GENERATED_BODY()

public:
	ADayNightCycle();

	// one full day in seconds of game time
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	float DayLength = 240.f;

	// the hour the game starts at (0..24)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	float StartHour = 9.f;

	// compass direction of the sun's path (yaw of the light), degrees
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	float SunYaw = -116.f;

	// found on the level if empty
	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Day Night")
	TObjectPtr<ADirectionalLight> Sun;

	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Day Night")
	TObjectPtr<AActor> SkySphere;

	// street lamps: working ones light up at night, broken ones flicker
	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Day Night")
	TArray<TObjectPtr<AActor>> StreetLamps;

	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Day Night")
	TArray<TObjectPtr<AActor>> BrokenStreetLamps;

	// the sun and the moon in the sky: perfectly round discs far away (the sky sphere's own sun is switched off)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	UMaterialInterface* SunMaterial;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	UMaterialInterface* MoonMaterial;

	// diameters (cm) at DiscDistance: 2200 cm at 600 m is about 2 degrees
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	float SunDiscSize = 2400.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	float MoonDiscSize = 2000.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	float DiscDistance = 60000.f;

	// the colour of the night: it stays blue, not black
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	FLinearColor NightTint = FLinearColor(0.45f, 0.58f, 1.f);

	// brightness of a working street lamp at night
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Day Night")
	float StreetLampCandelas = 700.f;

	UFUNCTION(BlueprintPure, Category = "Day Night")
	float GetHour() const { return Hour; }

	// 0 at night .. 1 in full daylight
	UFUNCTION(BlueprintPure, Category = "Day Night")
	float GetDaylight() const { return Daylight; }

	virtual void Tick(float DeltaTime) override;

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, Category = "Day Night")
	UDirectionalLightComponent* Moon;

	UPROPERTY(VisibleAnywhere, Category = "Day Night")
	UStaticMeshComponent* SunDisc;

	UPROPERTY(VisibleAnywhere, Category = "Day Night")
	UStaticMeshComponent* MoonDisc;

	// exposure: the night has to stay dark (auto exposure would brighten it up)
	UPROPERTY(VisibleAnywhere, Category = "Day Night")
	UPostProcessComponent* Grading;

private:
	void FindLevelActors();
	void SetupStreetLamps();
	void Apply();
	void RefreshSky(float CloudOpacity);
	void PlaceDiscs();
	void SetSkyNumber(const TCHAR* Name, float Value, float* OutOld = nullptr);

	float Hour = 9.f;
	float Daylight = 1.f;

	// the level's values at start: everything is scaled from them
	float SunIntensity = 3.f;
	float SkyIntensity = 1.f;
	float FogDensity = 0.03f;
	FLinearColor FogColor = FLinearColor::White;
	float SkyCloudOpacity = -1.f;
	float NextSkyRefresh = 0.f;
	float NextSkyRecapture = 0.f;

	UPROPERTY()
	TObjectPtr<ASkyLight> SkyLight;

	UPROPERTY()
	TObjectPtr<AExponentialHeightFog> Fog;

	UPROPERTY()
	TObjectPtr<ARainWeather> Rain;

	UPROPERTY()
	TArray<TObjectPtr<USpotLightComponent>> LampLights;
};
