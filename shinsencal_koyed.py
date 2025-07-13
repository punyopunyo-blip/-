import os
import math
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, TextInputStyle
from nextcord.ui import View, Select, Modal, TextInput

intents = nextcord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

BASE_ATK = {"兵器": 100, "槍": 40, "騎": 40, "弓": 40, "盾": 40}
RATING = {"S": 1.2, "A": 1.0, "B": 0.8, "C": 0.7}

def calc_unit_attack(兵種: str, ratings: list[str]) -> (int, str):
    base = BASE_ATK.get(兵種, 0)
    coef_list = [RATING.get(r.strip().upper(), 0) for r in ratings]
    total = int(sum(base * c for c in coef_list))
    formula = f"{base} × ({' + '.join([str(c) for c in coef_list])})"
    return total, formula

class SiegeModal(Modal):
    def __init__(self, selected_type: str):
        super().__init__(title="攻城条件入力")
        self.selected_type = selected_type

        self.rating1 = TextInput(label="武将①の適正（S/A/B/C）", placeholder="例: S", style=TextInputStyle.short)
        self.rating2 = TextInput(label="武将②の適正", placeholder="例: A", style=TextInputStyle.short)
        self.rating3 = TextInput(label="武将③の適正", placeholder="例: B", style=TextInputStyle.short)
        self.durability = TextInput(label="城の耐久値", placeholder="例: 50000", style=TextInputStyle.short)
        self.units = TextInput(label="攻城参加部隊数", placeholder="例: 3", style=TextInputStyle.short)

        self.add_item(self.rating1)
        self.add_item(self.rating2)
        self.add_item(self.rating3)
        self.add_item(self.durability)
        self.add_item(self.units)

    async def callback(self, interaction: Interaction):
        ratings_raw = [self.rating1.value, self.rating2.value, self.rating3.value]
        ratings_up = [r.strip().upper() for r in ratings_raw]
        if not all(r in RATING for r in ratings_up):
            await interaction.response.send_message(
                "⚠️ 適正は S / A / B / C のいずれかで入力してください（半角・小文字もOK）",
                ephemeral=True
            )
            return

        try:
            durability = int(self.durability.value)
            units = int(self.units.value)
            if durability <= 0 or units <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "⚠️ 城の耐久値と攻城参加部隊数には 1以上の半角数字を入力してください",
                ephemeral=True
            )
            return

        unit_attack, formula = calc_unit_attack(self.selected_type, ratings_up)
        total_attack = unit_attack * units
        turns = durability / total_attack
        sec = int(turns * 300)
        minutes, seconds = divmod(sec, 60)
        timeout_msg = "✅ 時間内に落城可能！" if turns <= 9 else "⏳ 時間切れ：最大 9ターンを超過"

        extra_msg = ""
        if turns > 9:
            min_units = math.ceil(durability / (unit_attack * 8))
            extra_msg = f"🛠️ 8ターン以内で落城させるには、最低攻城参加部隊数: {min_units} 部隊が必要です\n"

        summary = (
            f"📝 入力内容の確認：\n"
            f"・兵種：{self.selected_type}\n"
            f"・武将①の適正：{ratings_up[0]}\n"
            f"・武将②の適正：{ratings_up[1]}\n"
            f"・武将③の適正：{ratings_up[2]}\n"
            f"・城の耐久値：{durability}\n"
            f"・攻城参加部隊数：{units}\n\n"
        )
        result = (
            f"🏯 総攻城値: {total_attack}（ユニット攻城値: {unit_attack} = {formula}）\n"
            f"※ この攻城値には兵器研究Lvや施設による補正は含まれていません\n"
            f"⚔️ 推定ターン数: {turns:.1f} ターン\n"
            f"🕒 所要時間: 約 {minutes}分 {seconds}秒\n"
            f"{timeout_msg}\n"
            f"{extra_msg}"
        )

        await interaction.response.send_message(summary + result, ephemeral=False)

class SiegeView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.type_select = Select(
            placeholder="兵種を選択（部隊共通）",
            options=[nextcord.SelectOption(label=k) for k in BASE_ATK.keys()]
        )
        self.type_select.callback = self.select_type
        self.add_item(self.type_select)

    async def select_type(self, interaction: Interaction):
        selected_type = interaction.data["values"][0]
        await interaction.response.send_modal(SiegeModal(selected_type))

@bot.slash_command(name="攻城", description="兵種と適正から攻城値を計算します")
async def siege(interaction: Interaction):
    await interaction.response.send_message("⚔️ 兵種を選択してください：", view=SiegeView(), ephemeral=True)

# ✅ Bot起動（環境変数方式）
bot.run(os.getenv("BOT_TOKEN"))