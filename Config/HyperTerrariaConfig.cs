using System.ComponentModel;
using Terraria.ModLoader.Config;

namespace HyperTerraria.Config;

/// <summary>
/// Preferências locais do jogador. Esta configuração não é sincronizada com
/// servidores porque o mod altera apenas textos exibidos no cliente.
/// </summary>
public sealed class HyperTerrariaConfig : ModConfig
{
	public override ConfigScope Mode => ConfigScope.ClientSide;

	[DefaultValue(true)]
	public bool EnableItemNames;

	[DefaultValue(true)]
	public bool LogChangedItems;
}

