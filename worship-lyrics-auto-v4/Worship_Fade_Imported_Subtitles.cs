using System;
using System.Windows.Forms;
using ScriptPortal.Vegas;

public class EntryPoint
{
    private const double FadeSeconds = 0.25;

    public void FromVegas(Vegas vegas)
    {
        int count = 0;

        foreach (Track tr in vegas.Project.Tracks)
        {
            if (!(tr is VideoTrack)) continue;
            foreach (TrackEvent te in tr.Events)
            {
                VideoEvent ve = te as VideoEvent;
                if (ve == null || !ve.Selected || !IsTitlesText(ve)) continue;
                Apply(ve);
                count++;
            }
        }

        if (count == 0)
        {
            foreach (Track tr in vegas.Project.Tracks)
            {
                if (!(tr is VideoTrack)) continue;
                int local = 0;

                foreach (TrackEvent te in tr.Events)
                {
                    VideoEvent ve = te as VideoEvent;
                    if (ve == null || !IsTitlesText(ve)) continue;
                    Apply(ve);
                    local++;
                }

                if (local > 0)
                {
                    count = local;
                    break;
                }
            }
        }

        MessageBox.Show(
            count.ToString() + " subtitle event(s) updated.\n\nFade In/Out: 0.25 sec",
            "Worship Subtitle Fade"
        );
    }

    private bool IsTitlesText(VideoEvent ve)
    {
        try
        {
            return ve.ActiveTake != null
                && ve.ActiveTake.Media != null
                && ve.ActiveTake.Media.Generator != null
                && ve.ActiveTake.Media.Generator.PlugIn.Name == "Titles & Text";
        }
        catch { return false; }
    }

    private void Apply(VideoEvent ve)
    {
        Timecode wanted = Timecode.FromSeconds(FadeSeconds);
        long maxNanos = ve.Length.Nanos / 3;
        Timecode actual = wanted;
        if (actual.Nanos > maxNanos)
            actual = Timecode.FromNanos(maxNanos);

        ve.FadeIn.Length = actual;
        ve.FadeOut.Length = actual;
        ve.FadeIn.Curve = CurveType.Smooth;
        ve.FadeOut.Curve = CurveType.Smooth;
    }
}
