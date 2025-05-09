import abc


class ChatbotCheck(abc.ABC):
    @abc.abstractmethod
    def __str__(self):
        """
        Each check should define a `_str_` method that
        returns the code used to generate the check.

        Example:

        If `Response.equals("ABC")` produces the internal
        type `ChatbotResponseEquals("ABC")`, the __str__
        method should return 'Response.equals("ABC")'.
        """

    @abc.abstractmethod
    def find_error(self, value, **kwargs):
        """ """

    def check(self, value, **kwargs):
        exception = self.find_error(value, **kwargs)
        if exception:
            raise exception
