from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """
        Extrai a URL da foto de perfil do extra_data e a salva no CustomUser.
        """
        user = super(CustomSocialAccountAdapter, self).save_user(
            request, sociallogin, form
        )

        picture_url = sociallogin.account.extra_data.get("picture")

        if picture_url:
            if picture_url.startswith("http://"):
                picture_url = "https://" + picture_url[7:]

            user.profile_picture_url = picture_url
            user.save()

        return user

    def pre_social_login(self, request, sociallogin):
        """
        Invoked just prior to a social login.
        If the user already exists and logs in again via social account,
        update their profile picture if available.
        """
        if sociallogin.is_existing:
            user = sociallogin.user
            picture_url = sociallogin.account.extra_data.get("picture")

            if picture_url and user.profile_picture_url != picture_url:
                if picture_url.startswith("http://"):
                    picture_url = "https://" + picture_url[7:]
                user.profile_picture_url = picture_url
                user.save()
