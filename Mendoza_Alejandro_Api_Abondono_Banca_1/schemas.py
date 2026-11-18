from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
    field_validator,
)


class ClienteInput(BaseModel):
    """Datos crudos de un cliente necesarios para predecir el abandono."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )

    # Identificador: se conserva para la respuesta, NO entra al modelo.
    id_cliente: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Código del cliente.",
    )

    # --- Variables numéricas ---
    edad: int = Field(..., ge=18, le=100)
    ingresos_anuales: float = Field(..., ge=0)
    antiguedad_meses: int = Field(..., ge=0, le=900)
    saldo_cuenta: float = Field(...)
    num_productos: int = Field(..., ge=1, le=10)

    # Nivel de satisfacción: escala de 1 a 5
    nivel_satisfaccion: int = Field(
        ...,
        ge=1,
        le=5,
        description="Nivel de satisfacción del cliente (1-5).",
    )

    # --- Variable booleana ---
    tiene_tarjeta: bool = Field(
        ...,
        description="Tiene tarjeta (sí/no).",
    )

    # --- Variables categóricas ---
    nivel_estudios: Literal[
        "Sin estudios",
        "Primarios",
        "Secundarios",
        "FP",
        "Universitarios",
        "Posgrado",
    ]

    tipo_cuenta: Literal[
        "Corriente",
        "Ahorro",
        "Nómina",
        "Premium",
    ]

    canal_preferido: Literal[
        "Oficina",
        "Web",
        "App",
        "Teléfono",
    ]

    # --- Normalización de nivel de estudios ---
    @field_validator("nivel_estudios", mode="before")
    @classmethod
    def normalizar_estudios(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()

            equivalencias = {
                "grado": "Universitarios",
                "universitarios": "Universitarios",
                "universitario": "Universitarios",
                "fp": "FP",
                "posgrado": "Posgrado",
                "primarios": "Primarios",
                "secundarios": "Secundarios",
                "sin estudios": "Sin estudios",
            }

            return equivalencias.get(v, v)

        return v

    # --- Normalización del tipo de cuenta ---
    @field_validator("tipo_cuenta", mode="before")
    @classmethod
    def normalizar_tipo_cuenta(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()

            equivalencias = {
                "corriente": "Corriente",
                "ahorro": "Ahorro",
                "nómina": "Nómina",
                "nomina": "Nómina",
                "premium": "Premium",
            }

            return equivalencias.get(v, v)

        return v

    # --- Normalización del canal preferido ---
    @field_validator("canal_preferido", mode="before")
    @classmethod
    def normalizar_canal(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()

            equivalencias = {
                "oficina": "Oficina",
                "web": "Web",
                "app": "App",
                "app movil": "App",
                "app móvil": "App",
                "teléfono": "Teléfono",
                "telefono": "Teléfono",
            }

            return equivalencias.get(v, v)

        return v

    # --- Validación de coherencia entre edad y antigüedad ---
    @model_validator(mode="after")
    def antiguedad_coherente_con_edad(self):
        """No se puede llevar más meses de cliente que meses de adulto."""

        if self.antiguedad_meses > (self.edad - 18) * 12:
            raise ValueError(
                "antiguedad_meses no puede superar los meses "
                "transcurridos desde los 18 años de edad."
            )

        return self


class PrediccionOutput(BaseModel):
    """Respuesta estructurada de la API tras la inferencia."""

    id_cliente: str = Field(
        ...,
        description="Código del cliente analizado.",
    )

    abandono: Literal[0, 1] = Field(
        ...,
        description="0 = permanece, 1 = abandono.",
    )

    probabilidad_abandono: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probabilidad estimada de fuga (0.0-1.0).",
    )

    nivel_riesgo: Literal["Bajo", "Medio", "Alto"] = Field(
        ...,
        description="Clasificación operativa del riesgo.",
    )

    accion_recomendada: str = Field(
        ...,
        min_length=1,
        description="Sugerencia comercial para el gestor.",
    )


def clasificar_riesgo(probabilidad: float) -> tuple[str, str]:
    """Devuelve nivel de riesgo y acción recomendada."""

    if probabilidad < 0.30:
        return (
            "Bajo",
            "Mantener la relación habitual; sin acción especial.",
        )

    if probabilidad < 0.60:
        return (
            "Medio",
            "Contactar proactivamente y ofrecer productos o ventajas.",
        )

    return (
        "Alto",
        "Llamada prioritaria del gestor con oferta de retención.",
    )