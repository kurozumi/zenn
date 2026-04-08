## 全体の流れ

1. CLAUDE.md を準備（初回のみ）
2. issue を選ぶ
3. worktree でブランチを作成
4. Claude Code に修正を依頼
5. PR を作成（プロンプトで指示するだけ）

## 1. CLAUDE.md を準備する（初回のみ）

Claude Code はプロジェクトルートの `CLAUDE.md` を読み込んで、プロジェクト固有のルールを理解します。EC-CUBE へのコントリビュート用に CLAUDE.md を作成しておくと、毎回指示しなくても適切な PR を作成してくれます。

### フォークとクローン


### upstream の設定


### CLAUDE.md の作成


これで Claude Code が EC-CUBE のコントリビュートルールを理解した状態で作業できます。

## 2. issue を選ぶ

Claude Code を起動して issue を確認します。


プロンプトで指示するだけで、Claude Code が gh コマンドを実行します。

### プロンプト例


### Claude Code が実行するコマンド


`good-first-issue` ラベルが付いている issue は、初めてのコントリビュートに適しています。



### 具体例：issue #6582




## 3. worktree でブランチを作成

複数の issue を並行して作業する場合、`git worktree` が便利です。ブランチごとに別のディレクトリで作業できます。

### 最新の main を取得


### worktree でブランチを作成


### CLAUDE.md をシンボリックリンク

worktree で作成したディレクトリには CLAUDE.md がありません。main ブランチの CLAUDE.md をシンボリックリンクすると、どの worktree でも同じルールで作業できます。


ℹ️ シンボリックリンクにすることで、CLAUDE.md を更新したときにすべての worktree に反映されます。

### worktree の一覧確認



## 4. Claude Code に修正を依頼

worktree のディレクトリで Claude Code を起動します。


### プロンプト例


Claude Code が自動的に以下を実行します：

1. **ファイルを読み込み**
2. **問題を特定**
3. **修正を実装**

### Claude Code の動作例



Claude Code が問題を特定し、修正案を提示します。


Bootstrap 5 では `data-bs-toggle` は1つの要素に1つしか指定できないため、ボタンを `<span>` でラップしてツールチップを外側に付けます。

## 5. PR を作成（プロンプトで指示するだけ）

修正が完了したら、プロンプトで PR 作成を指示するだけです。

### プロンプト例


**これだけで OK です。** Claude Code が CLAUDE.md のルールに従って、以下を自動実行します。

### Claude Code が実行するコマンド


CLAUDE.md にルールを書いておくことで、毎回細かく指示しなくても適切な PR が作成されます。

## worktree の後片付け

PR がマージされたら、worktree を削除します。


## CLAUDE.md をさらに充実させる

プロジェクトに慣れてきたら、CLAUDE.md に追加のルールを書いておくとさらに便利です。


## まとめ

| ポイント | 効果 |
|---------|------|
| CLAUDE.md を準備 | 毎回指示しなくても適切な PR が作成される |
| worktree を使用 | 複数の issue を並行して作業できる |
| シンボリックリンク | すべての worktree で同じルールを適用 |
| プロンプトで指示 | コマンドを覚えなくても PR まで完了 |

Claude Code + CLAUDE.md + worktree の組み合わせで、EC-CUBE へのコントリビュートがスムーズになります。まずは `good-first-issue` から始めて、OSS コントリビュートに挑戦してみてください。

## 参考リンク

- [EC-CUBE GitHub](https://github.com/EC-CUBE/ec-cube)
- [EC-CUBE 開発者向けドキュメント](https://doc4.ec-cube.net/)
- [EC-CUBE コントリビューションガイド](https://github.com/EC-CUBE/ec-cube/blob/4.3/CONTRIBUTING.md)
- [Git Worktree ドキュメント](https://git-scm.com/docs/git-worktree)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---