"""HTML email templates for Nakama transactional emails.

All templates use inline CSS for maximum email client compatibility
(Gmail, Outlook, Apple Mail, etc. strip <style> tags).
"""
from __future__ import annotations


def email_template(
    *,
    title: str,
    greeting: str,
    message: str,
    button_text: str,
    button_url: str,
    footer: str = "",
) -> str:
    """Render a branded HTML email with a CTA button.

    Parameters
    ----------
    title : str
        Big headline shown at the top of the email body.
    greeting : str
        Personalized greeting line (e.g. "Hi shenyo1,").
    message : str
        Body text explaining what the email is about.
    button_text : str
        Call-to-action button label.
    button_url : str
        URL the button links to.
    footer : str, optional
        Small muted text shown below the button (e.g. expiry notice).

    Returns
    -------
    str
        Complete HTML document string.
    """
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#0f0f17;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f17;min-height:100vh;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background-color:#1a1a2e;border-radius:12px;overflow:hidden;border:1px solid #2a2a4a;">

          <!-- Header -->
          <tr>
            <td style="padding:32px 40px 0 40px;text-align:center;">
              <h1 style="margin:0;font-size:28px;font-weight:800;color:#ff6b9d;letter-spacing:-0.02em;">
                Nakama
              </h1>
              <p style="margin:8px 0 0 0;font-size:13px;color:#8888aa;text-transform:uppercase;letter-spacing:0.1em;">
                Multi-source aggregation
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 40px 24px 40px;">
              <h2 style="margin:0 0 16px 0;font-size:22px;font-weight:700;color:#e8e8f0;">
                {title}
              </h2>
              <p style="margin:0 0 8px 0;font-size:16px;color:#c0c0d8;line-height:1.5;">
                {greeting}
              </p>
              <p style="margin:0 0 28px 0;font-size:15px;color:#a0a0b8;line-height:1.6;">
                {message}
              </p>

              <!-- CTA Button -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center">
                    <!--[if mso]>
                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{button_url}" style="height:48px;v-text-anchor:middle;width:240px;" arcsize="25%" strokecolor="#ff6b9d" fillcolor="#ff6b9d">
                    <w:anchorlock/>
                    <center style="color:#ffffff;font-family:sans-serif;font-size:16px;font-weight:600;">
                    {button_text}
                    </center>
                    </v:roundrect>
                    <![endif]-->
                    <!--[if !mso]><!-->
                    <a href="{button_url}"
                       style="display:inline-block;padding:14px 40px;font-size:16px;font-weight:600;color:#ffffff;background-color:#ff6b9d;border-radius:24px;text-decoration:none;border:2px solid #ff6b9d;transition:background-color 0.2s;">
                      {button_text}
                    </a>
                    <!--<![endif]-->
                  </td>
                </tr>
              </table>

              <!-- Link fallback (for clients that block buttons) -->
              <p style="margin:20px 0 0 0;font-size:13px;color:#666688;text-align:center;line-height:1.5;">
                If the button doesn't work, copy this link:<br>
                <a href="{button_url}" style="color:#ff6b9d;word-break:break-all;text-decoration:underline;">{button_url}</a>
              </p>

              {f'<p style="margin:24px 0 0 0;font-size:13px;color:#666688;text-align:center;line-height:1.5;border-top:1px solid #2a2a4a;padding-top:20px;">{footer}</p>' if footer else ''}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:0 40px 32px 40px;">
              <p style="margin:0;font-size:12px;color:#555577;text-align:center;line-height:1.5;">
                This email was sent by Nakama.<br>
                <a href="https://app.mynakama.web.id" style="color:#555577;text-decoration:none;">app.mynakama.web.id</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
