using System;
using System.Collections.Generic;
using System.Reflection;
using System.Text.Json;
using System.Text.RegularExpressions;
using HyperTerraria.Config;
using Terraria.Localization;
using Terraria.ModLoader;

namespace HyperTerraria.Systems;

/// <summary>
/// Carrega traduções previamente geradas e as aplica a nomes de itens vanilla.
/// Não há acesso à rede nem tradução em tempo real.
/// </summary>
public sealed class HyperItemTranslationSystem : ModSystem
{
	private const string CachePath = "Assets/hyper_items_ptBR.json";
	private const string ItemNamePrefix = "ItemName.";

	private static readonly Regex ItemNamePattern = new(
		@"^ItemName\.",
		RegexOptions.Compiled | RegexOptions.CultureInvariant
	);

	private Dictionary<string, string> _translations = new(StringComparer.Ordinal);
	private MethodInfo? _setValueMethod;

	public override void OnModLoad()
	{
		_translations = LoadTranslationCache();
		_setValueMethod = typeof(LocalizedText).GetMethod(
			"SetValue",
			BindingFlags.Instance | BindingFlags.NonPublic,
			binder: null,
			types: new[] { typeof(string) },
			modifiers: null
		);

		if (_setValueMethod is null)
		{
			Mod.Logger.Error(
				"LocalizedText.SetValue(string) não foi encontrado. " +
				"As traduções não poderão ser aplicadas nesta versão do tModLoader."
			);
		}
	}

	public override void OnLocalizationsLoaded()
	{
		if (!ModContent.GetInstance<HyperTerrariaConfig>().EnableItemNames)
		{
			Mod.Logger.Info("Substituição de nomes de itens desativada na configuração.");
			return;
		}

		if (_translations.Count == 0 || _setValueMethod is null)
			return;

		int changed = 0;

		try
		{
			// FindAll garante que apenas chaves já carregadas pelo Terraria sejam
			// consideradas; entradas desconhecidas do JSON são simplesmente ignoradas.
			foreach (LocalizedText localizedText in LanguageManager.Instance.FindAll(ItemNamePattern))
			{
				if (!_translations.TryGetValue(localizedText.Key, out string? translatedValue))
					continue;

				try
				{
					_setValueMethod.Invoke(localizedText, new object[] { translatedValue });
					changed++;

					if (ModContent.GetInstance<HyperTerrariaConfig>().LogChangedItems)
						Mod.Logger.Info($"{localizedText.Key} => {translatedValue}");
				}
				catch (Exception exception)
				{
					Mod.Logger.Warn(
						$"Não foi possível alterar '{localizedText.Key}': {UnwrapMessage(exception)}"
					);
				}
			}

			Mod.Logger.Info($"{changed} nome(s) de item hypertraduzido(s).");
		}
		catch (Exception exception)
		{
			// Uma alteração interna no sistema de localização não deve impedir o
			// carregamento do jogo ou dos demais mods.
			Mod.Logger.Error(
				$"Falha ao procurar localizações ItemName.*: {UnwrapMessage(exception)}"
			);
		}
	}

	public override void Unload()
	{
		_translations.Clear();
		_setValueMethod = null;
	}

	private Dictionary<string, string> LoadTranslationCache()
	{
		var result = new Dictionary<string, string>(StringComparer.Ordinal);

		try
		{
			byte[] jsonBytes = Mod.GetFileBytes(CachePath);

			if (jsonBytes.Length == 0)
			{
				Mod.Logger.Warn($"O cache '{CachePath}' está vazio.");
				return result;
			}

			Dictionary<string, string?>? parsed = JsonSerializer.Deserialize<Dictionary<string, string?>>(
				jsonBytes,
				new JsonSerializerOptions
				{
					AllowTrailingCommas = true,
					ReadCommentHandling = JsonCommentHandling.Skip
				}
			);

			if (parsed is null)
			{
				Mod.Logger.Warn($"O cache '{CachePath}' não contém um objeto JSON válido.");
				return result;
			}

			foreach ((string key, string? value) in parsed)
			{
				if (!key.StartsWith(ItemNamePrefix, StringComparison.Ordinal))
				continue;

				if (string.IsNullOrWhiteSpace(value))
				continue;

				result[key] = value;
			}

			Mod.Logger.Info($"{result.Count} tradução(ões) ItemName.* carregada(s) do cache.");
		}
		catch (Exception exception)
		{
			// GetFileBytes também lança exceção quando o arquivo não foi empacotado.
			Mod.Logger.Error(
				$"Não foi possível carregar '{CachePath}'. O mod continuará sem substituir textos. " +
				UnwrapMessage(exception)
			);
		}

		return result;
	}

	private static string UnwrapMessage(Exception exception) =>
		exception is TargetInvocationException { InnerException: not null }
			? exception.InnerException.Message
			: exception.Message;
}

