<?php //子テーマ用関数
if ( !defined( 'ABSPATH' ) ) exit;

//子テーマ用のビジュアルエディタースタイルを適用
add_editor_style();

//以下に子テーマ用の関数を書く

/**
 * 記事下CTAの設定を返す
 * 将来カテゴリ別に出し分ける場合は、この関数内で条件分岐を追加する
 *
 * @return array
 */
function sateilab_get_post_cta_data() {
  return array(
    'title'       => '愛車を少しでも高く売りたいなら、先に査定相場を確認しておきましょう',
    'description' => '1社だけで決めると、本来より安い査定額になることがあります。まずは複数の選択肢を比較して、愛車の相場感をつかんでおくのがおすすめです。',
    'primary_text'=> '無料で査定相場をチェックする',
    'primary_url' => 'https://px.a8.net/svt/ejp?a8mat=457BCE+A4DBRU+14EG+61Z82',
    'secondary_text' => '他の記事も見る',
    'secondary_url'  => 'https://satei-lab.com/',
    'note'        => '※提携先サイトへ移動します。申し込み前に対象エリアや条件をご確認ください。',
  );
}

/**
 * 記事下CTAのHTMLを生成する
 *
 * @return string
 */
function sateilab_get_post_cta_html() {
  $cta = sateilab_get_post_cta_data();

  $html  = '<div class="sl-cta">';
  $html .= '<p class="sl-cta__title">' . esc_html( $cta['title'] ) . '</p>';
  $html .= '<p class="sl-cta__text">' . esc_html( $cta['description'] ) . '</p>';
  $html .= '<div class="sl-cta__actions">';
  $html .= '<a class="sl-btn sl-btn--primary" href="' . esc_url( $cta['primary_url'] ) . '">' . esc_html( $cta['primary_text'] ) . '</a>';
  $html .= '<a class="sl-btn sl-btn--secondary" href="' . esc_url( $cta['secondary_url'] ) . '">' . esc_html( $cta['secondary_text'] ) . '</a>';
  $html .= '</div>';
  $html .= '<p class="sl-cta__text">' . esc_html( $cta['note'] ) . '</p>';
  $html .= '</div>';

  return $html;
}

/**
 * 投稿ページの本文末尾に共通CTAを追加する
 *
 * @param string $content 本文
 * @return string
 */
function sateilab_append_post_cta_to_content( $content ) {
  if ( is_admin() || !is_singular( 'post' ) || !in_the_loop() || !is_main_query() ) {
    return $content;
  }

  return $content . sateilab_get_post_cta_html();
}
add_filter( 'the_content', 'sateilab_append_post_cta_to_content' );
