# HyperTerraria

Mod client-side para tModLoader 1.4.x que substitui nomes de itens vanilla por
versões hypertraduzidas em português.

Hypertranslation faz um texto passar por vários idiomas antes de retornar ao
português. O HyperTerraria **não traduz nada durante o jogo**: ele lê traduções
prontas de `Assets/hyper_items_ptBR.json`. Não há chamadas de API, dependências
externas ou chaves secretas.

## Requisitos

- Terraria e tModLoader 1.4.x instalados.
- Windows com PowerShell para usar os scripts opcionais.
- Git, caso o projeto seja clonado.

## Instalação

1. Clone o repositório:

   ```powershell
   git clone <URL-DO-REPOSITORIO> HyperTerraria
   cd HyperTerraria
   ```

2. A pasta padrão de fontes de mods no Windows é:

   ```text
   %USERPROFILE%\Documents\My Games\Terraria\tModLoader\ModSources
   ```

   Em instalações nas quais a pasta Documentos foi movida pelo Windows ou
   OneDrive, localize a pasta equivalente usada pelo tModLoader.

3. Escolha uma destas formas de instalar:

   - Copie a pasta inteira do repositório para `ModSources\HyperTerraria`.
   - Para copiar e atualizar o destino automaticamente:

     ```powershell
     powershell -ExecutionPolicy Bypass -File .\scripts\copy-to-modsources.ps1
     ```

   - Para criar um link simbólico e editar o clone diretamente:

     ```powershell
     powershell -ExecutionPolicy Bypass -File .\scripts\install-to-modsources.ps1
     ```

     A criação do link exige o Modo de Desenvolvedor do Windows ou um
     PowerShell executado como administrador. O destino não pode existir.

## Compilar, testar e ativar

1. Abra o tModLoader.
2. Acesse **Workshop > Develop Mods**.
3. Encontre `HyperTerraria` e escolha **Build + Reload**.
4. Volte ao menu de Workshop, abra **Manage Mods**, ative `HyperTerraria` e
   selecione **Reload Mods** quando solicitado.
5. Entre em um mundo e confira os nomes dos itens presentes no cache.
6. Em **Settings > Mod Configuration > HyperTerraria**, use:
   - `EnableItemNames`: liga ou desliga a substituição de nomes.
   - `LogChangedItems`: registra cada substituição no log do tModLoader.

Se o JSON estiver ausente, vazio ou inválido, o mod registra o problema e
continua carregando sem substituir nomes.

## Editar as hypertraduções

Edite `Assets/hyper_items_ptBR.json` mantendo um objeto JSON no formato:

```json
{
  "ItemName.CopperShortsword": "Espada curta de cobre que viajou demais",
  "ItemName.IronPickaxe": "Picareta de ferro internacionalmente confusa"
}
```

As chaves precisam corresponder às chaves vanilla e começar com `ItemName.`.
Valores vazios e outros prefixos são ignorados. Salve o arquivo em UTF-8 e use
**Build + Reload** novamente. JSON não aceita duas entradas com a mesma chave;
também é recomendável não deixar vírgula depois da última entrada.

## Como funciona

Durante `OnModLoad`, o sistema desserializa o cache empacotado. Depois que as
localizações do jogo são carregadas, `OnLocalizationsLoaded` procura chaves
`ItemName.*`, encontra as que também estão no cache e chama por reflection o
método não público `LocalizedText.SetValue`. Essa reflection é necessária
porque textos vanilla não expõem um setter público.

O mod só muda localização no cliente. Não altera itens, receitas, atributos,
gameplay ou arquivos da instalação do Terraria.

## Expansão futura

Para adicionar NPCs e bosses, crie caches e sistemas equivalentes para o
prefixo `NPCName.`. O mesmo padrão pode ser usado para `ItemTooltip.`,
`BuffName.` e outros grupos:

1. carregue apenas entradas do prefixo permitido;
2. encontre apenas localizações já registradas pelo Terraria;
3. respeite uma opção client-side própria;
4. aplique os valores somente em `OnLocalizationsLoaded`;
5. mantenha falhas de cache e reflection não fatais.

Essa separação evita misturar grupos e mantém claro quais textos cada versão
do mod pode modificar.

