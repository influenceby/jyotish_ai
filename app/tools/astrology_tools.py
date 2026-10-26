from typing import Dict

from pydantic import BaseModel, Field

from app.services.astrology_service import astrology_service


# ============================================================
# BIRTH DETAILS SCHEMA
# ============================================================

class BirthDetails(BaseModel):
    """
    Exact birth details required by the Astrology API.
    """

    day: int = Field(description="Day of birth")
    month: int = Field(description="Month of birth")
    year: int = Field(description="Year of birth")

    hour: int = Field(
        description="Hour of birth in 24-hour format"
    )

    minute: int = Field(
        description="Minute of birth"
    )

    latitude: float = Field(
        description="Birth place latitude"
    )

    longitude: float = Field(
        description="Birth place longitude"
    )

    timezone: float = Field(
        default=5.5,
        description="Timezone offset from UTC"
    )


# ============================================================
# ASTROLOGY TOOLS
# ============================================================

class AstrologyTools:

    # ---------------------------------------------------------
    # COMMON HELPER
    # ---------------------------------------------------------

    @staticmethod
    def build_payload(
        day: int,
        month: int,
        year: int,
        hour: int,
        minute: int,
        latitude: float,
        longitude: float,
        timezone: float = 5.5,
    ) -> Dict[str, object]:

        return {
            "day": day,
            "month": month,
            "year": year,
            "hour": hour,
            "min": minute,
            "lat": latitude,
            "lon": longitude,
            "tzone": timezone,
        }


    # ---------------------------------------------------------
    # 1. BASIC ASTRO DETAILS
    # ---------------------------------------------------------

    def get_astro_details(
        self,
        birth_details: BirthDetails,
    ) -> Dict[str, object]:

        print("\n🔧 TOOL CALLED: get_astro_details")

        payload = self.build_payload(
            **birth_details.model_dump()
        )

        return astrology_service.call_api(
            endpoint="astro_details",
            payload=payload,
        )


    # ---------------------------------------------------------
    # 2. PLANETS
    # ---------------------------------------------------------

    def get_planets(
        self,
        birth_details: BirthDetails,
    ) -> list[Dict[str, object]]:

        print("\n🔧 TOOL CALLED: get_planets")

        payload = self.build_payload(
            **birth_details.model_dump()
        )

        return astrology_service.call_api(
            endpoint="planets/extended",
            payload=payload,
        )


    # ---------------------------------------------------------
    # 3. DIVISIONAL CHART
    # ---------------------------------------------------------

    def get_divisional_chart(
        self,
        birth_details: BirthDetails,
        chart_id: str,
    ) -> list[Dict[str, object]]:

        print(
            f"\n🔧 TOOL CALLED: get_divisional_chart ({chart_id})"
        )

        payload = self.build_payload(
            **birth_details.model_dump()
        )

        endpoint = f"horo_chart/{chart_id}"

        return astrology_service.call_api(
            endpoint=endpoint,
            payload=payload,
        )


    # ---------------------------------------------------------
    # 4. CURRENT DASHA
    # ---------------------------------------------------------

    def get_current_dasha(
        self,
        birth_details: BirthDetails,
    ) -> Dict[str, object]:

        print("\n🔧 TOOL CALLED: get_current_dasha")

        payload = self.build_payload(
            **birth_details.model_dump()
        )

        return astrology_service.call_api(
            endpoint="current_vdasha",
            payload=payload,
        )


    # ---------------------------------------------------------
    # 5. MAJOR YOGAS
    # ---------------------------------------------------------

    def get_major_yogas(
        self,
        birth_details: BirthDetails,
    ) -> Dict[str, object]:

        print("\n🔧 TOOL CALLED: get_major_yogas")

        payload = self.build_payload(
            **birth_details.model_dump()
        )

        return astrology_service.call_api(
            endpoint="major_yoga_details",
            payload=payload,
        )


    # ---------------------------------------------------------
    # 6. DOSHAS
    # ---------------------------------------------------------

    def get_doshas(
        self,
        birth_details: BirthDetails,
    ) -> Dict[str, object]:

        print("\n🔧 TOOL CALLED: get_doshas")

        payload = self.build_payload(
            **birth_details.model_dump()
        )

        manglik = astrology_service.call_api(
            endpoint="manglik",
            payload=payload,
        )

        kalsarpa = astrology_service.call_api(
            endpoint="kalsarpa_details",
            payload=payload,
        )

        sadhesati = astrology_service.call_api(
            endpoint="sadhesati_current_status",
            payload=payload,
        )

        return {
            "manglik": manglik,
            "kalsarpa": kalsarpa,
            "sadhesati": sadhesati,
        }


    # ---------------------------------------------------------
    # 7. ASHTAKAVARGA
    # ---------------------------------------------------------

    def get_ashtakavarga(
        self,
        birth_details: BirthDetails,
    ) -> Dict[str, object]:

        print("\n🔧 TOOL CALLED: get_ashtakavarga")

        payload = self.build_payload(
            **birth_details.model_dump()
        )

        return astrology_service.call_api(
            endpoint="sarvashtak",
            payload=payload,
        )


    # ---------------------------------------------------------
    # 8. GEMSTONE ANALYSIS
    # ---------------------------------------------------------

    def get_gemstone_analysis(
        self,
        birth_details: BirthDetails,
    ) -> Dict[str, object]:

        print("\n🔧 TOOL CALLED: get_gemstone_analysis")

        payload = self.build_payload(
            **birth_details.model_dump()
        )

        return astrology_service.call_api(
            endpoint="basic_gem_suggestion",
            payload=payload,
        )


# ============================================================
# SINGLETON
# ============================================================

astrology_tools = AstrologyTools()
